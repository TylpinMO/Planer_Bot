"""Обработчики для работы с задачами"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.crud import TaskCRUD, TaskListCRUD
from bot.keyboards.inline import (
    task_keyboard,
    list_details_keyboard,
    cancel_keyboard,
    tasks_list_keyboard,
    InlineKeyboardButton
)

router = Router()


async def get_owned_task(session: AsyncSession, task_id: int, user: User):
    """Не доверяем ID из callback или сохранённого состояния диалога."""
    task = await TaskCRUD.get_by_id(session, task_id)
    if task is None:
        return None
    task_list = await TaskListCRUD.get_by_id(session, task.list_id)
    if not task_list or task_list.user_id != user.id or not task_list.is_active:
        return None
    return task


class CreateTaskStates(StatesGroup):
    """Состояния для создания задачи"""
    waiting_for_text = State()
    waiting_for_notification = State()  # Для премиум пользователей


class SetTaskNotificationStates(StatesGroup):
    """Состояния для настройки уведомления задачи"""
    waiting_for_time = State()


@router.callback_query(F.data.startswith("add_task_"))
async def add_task_start(callback: CallbackQuery, session: AsyncSession, user: User, state: FSMContext):
    """Начать добавление задачи"""
    list_id = int(callback.data.split("_")[2])
    
    task_list = await TaskListCRUD.get_by_id(session, list_id)
    
    if not task_list or task_list.user_id != user.id or not task_list.is_active:
        await callback.answer("❌ Список не найден", show_alert=True)
        return
    
    text = f"""
✏️ <b>Добавление задачи</b>

📝 Список: {task_list.name}

Введите текст задачи:
"""
    
    await callback.message.edit_text(
        text=text,
        reply_markup=cancel_keyboard()
    )
    await state.set_state(CreateTaskStates.waiting_for_text)
    await state.update_data(list_id=list_id)
    await callback.answer()


@router.message(CreateTaskStates.waiting_for_text)
async def add_task_finish(message: Message, session: AsyncSession, state: FSMContext, user: User):
    """Завершить добавление задачи"""
    task_text = (message.text or "").strip()
    
    if len(task_text) < 1:
        await message.answer("❌ Текст задачи не может быть пустым.")
        return
    
    if len(task_text) > 1000:
        await message.answer("❌ Текст задачи слишком длинный. Максимум 1000 символов.")
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    list_id = data.get("list_id")
    
    task_list = await TaskListCRUD.get_by_id(session, list_id)
    if not task_list or task_list.user_id != user.id or not task_list.is_active:
        await message.answer("❌ Список не найден")
        await state.clear()
        return

    # Создаем задачу
    task = await TaskCRUD.create(session, list_id, task_text)
    
    # Для премиум пользователей предлагаем сразу настроить уведомление
    if user.is_premium:
        text = f"""
✅ <b>Задача добавлена!</b>

{task.text}

🔔 <b>Хотите настроить уведомление для этой задачи?</b>

Введите время в формате <b>HH:MM</b> (например, 09:00)
или нажмите "Пропустить", чтобы использовать общее уведомление списка.
"""
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip_task_notification_{task.id}")
        )
        
        await message.answer(
            text=text,
            reply_markup=builder.as_markup()
        )
        await state.set_state(CreateTaskStates.waiting_for_notification)
        await state.update_data(task_id=task.id, list_id=list_id)
    else:
        text = f"""
✅ <b>Задача добавлена!</b>

{task.text}

Вы можете добавить ещё задачи или вернуться к списку.
"""
        
        await message.answer(
            text=text,
            reply_markup=list_details_keyboard(list_id)
        )
        await state.clear()


@router.message(CreateTaskStates.waiting_for_notification)
async def set_new_task_notification(message: Message, session: AsyncSession, state: FSMContext, user: User):
    """Установить уведомление для новой задачи"""
    time_text = (message.text or "").strip()
    
    # Валидация формата времени
    try:
        hours, minutes = time_text.split(":")
        hours = int(hours)
        minutes = int(minutes)
        
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError
        
        time_formatted = f"{hours:02d}:{minutes:02d}"
    except:
        await message.answer("❌ Неверный формат времени. Используйте формат HH:MM (например, 09:00)")
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    task_id = data.get("task_id")
    list_id = data.get("list_id")
    
    task = await get_owned_task(session, task_id, user)
    if not task or not user.is_premium:
        await message.answer("❌ Задача недоступна для настройки уведомления")
        await state.clear()
        return
    list_id = task.list_id

    # Обновляем время уведомления
    await TaskCRUD.update_notification(session, task_id, time_formatted)
    
    text = f"""
✅ <b>Уведомление настроено!</b>

Вы будете получать уведомление в {time_formatted}

Вы можете добавить ещё задачи или вернуться к списку.
"""
    
    await message.answer(
        text=text,
        reply_markup=list_details_keyboard(list_id)
    )
    await state.clear()


@router.callback_query(F.data.startswith("skip_task_notification_"))
async def skip_task_notification(callback: CallbackQuery, state: FSMContext):
    """Пропустить настройку уведомления для задачи"""
    data = await state.get_data()
    list_id = data.get("list_id")
    
    text = """
✅ <b>Задача создана!</b>

Уведомление не установлено. Задача будет включена в общее уведомление списка.

Вы можете добавить ещё задачи или вернуться к списку.
"""
    
    await callback.message.edit_text(
        text=text,
        reply_markup=list_details_keyboard(list_id)
    )
    await state.clear()
    await callback.answer()


async def show_task_details(callback: CallbackQuery, session: AsyncSession, user: User):
    """Показать детали задачи (вспомогательная функция)"""
    task_id = int(callback.data.split("_")[1])
    
    task = await TaskCRUD.get_by_id(session, task_id)
    
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    task_list = await TaskListCRUD.get_by_id(session, task.list_id)
    
    if not task_list or task_list.user_id != user.id or not task_list.is_active:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    status = "✅ Выполнена" if task.is_completed else "⬜ Не выполнена"
    priority = {0: "Обычный", 1: "🔸 Средний", 2: "🔴 Высокий"}
    
    text = f"""
📌 <b>Задача</b>

{task.text}

<b>Статус:</b> {status}
<b>Приоритет:</b> {priority.get(task.priority, 'Обычный')}
"""
    
    if task.notification_time:
        text += f"\n🔔 <b>Уведомление:</b> {task.notification_time}"
    elif user.is_premium and not task.is_completed:
        text += f"\n\n💡 <i>Нажмите 🔔 Уведомление, чтобы настроить напоминание для этой задачи</i>"
    
    if task.deadline:
        text += f"\n⏰ <b>Дедлайн:</b> {task.deadline.strftime('%d.%m.%Y %H:%M')}"
    
    text += f"\n\n<i>Создано: {task.created_at.strftime('%d.%m.%Y %H:%M')}</i>"
    
    if task.is_completed and task.completed_at:
        text += f"\n<i>Выполнено: {task.completed_at.strftime('%d.%m.%Y %H:%M')}</i>"
    
    await callback.message.edit_text(
        text=text,
        reply_markup=task_keyboard(task_id, task.list_id, task.is_completed, user.is_premium)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task_notify_"))
async def set_task_notification_start(callback: CallbackQuery, user: User, state: FSMContext, session: AsyncSession):
    """Начать настройку уведомления для задачи (только премиум)"""
    if not user.is_premium:
        await callback.answer("⭐ Эта функция доступна только для премиум пользователей", show_alert=True)
        return
    
    task_id = int(callback.data.split("_")[2])
    
    if not await get_owned_task(session, task_id, user):
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return

    text = """
🔔 <b>Настройка уведомления для задачи</b>

<b>Премиум функция:</b> Установите индивидуальное время уведомления для этой задачи.

Введите время в формате <b>HH:MM</b>

Например: 09:00 или 18:30
"""
    
    await callback.message.edit_text(
        text=text,
        reply_markup=cancel_keyboard()
    )
    await state.set_state(SetTaskNotificationStates.waiting_for_time)
    await state.update_data(task_id=task_id)
    await callback.answer()


@router.callback_query(F.data.startswith("task_"))
async def handle_task_callback(callback: CallbackQuery, session: AsyncSession, user: User):
    """Обработчик callback для задач"""
    # Показываем детали задачи
    await show_task_details(callback, session, user)


@router.callback_query(F.data.startswith("toggle_task_"))
async def toggle_task_status(callback: CallbackQuery, session: AsyncSession, user: User):
    """Переключить статус выполнения задачи"""
    task_id = int(callback.data.split("_")[2])
    
    if not await get_owned_task(session, task_id, user):
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return

    task = await TaskCRUD.toggle_complete(session, task_id)
    
    status_text = "✅ Задача отмечена как выполненная!" if task.is_completed else "⬜ Задача снова активна!"
    
    await callback.answer(status_text)
    
    # Возвращаемся к списку задач с обновлением
    list_id = task.list_id
    task_list = await TaskListCRUD.get_by_id(session, list_id)
    tasks = await TaskCRUD.get_list_tasks(session, list_id, include_completed=False)
    completed_tasks = await TaskCRUD.get_list_tasks(session, list_id, include_completed=True)
    completed_count = len([t for t in completed_tasks if t.is_completed])
    
    notification_info = ""
    if task_list.notification_time:
        notification_info = f"\n🔔 Уведомления: {task_list.notification_time}"
    
    text = f"""
📋 <b>{task_list.name}</b>

Активных задач: {len(tasks)}
Выполнено: {completed_count}{notification_info}

{'<i>Все задачи выполнены! 🎉</i>' if not tasks else '<b>Нажмите на задачу, чтобы отметить её выполненной:</b>'}
"""
    
    try:
        if tasks:
            await callback.message.edit_text(
                text=text,
                reply_markup=tasks_list_keyboard(tasks, list_id)
            )
        else:
            await callback.message.edit_text(
                text=text,
                reply_markup=list_details_keyboard(list_id, task_list.notification_time is not None)
            )
    except Exception:
        pass


@router.callback_query(F.data.startswith("delete_task_"))
async def delete_task(callback: CallbackQuery, session: AsyncSession, user: User):
    """Удалить задачу"""
    task_id = int(callback.data.split("_")[2])
    
    task = await TaskCRUD.get_by_id(session, task_id)
    
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    task_list = await TaskListCRUD.get_by_id(session, task.list_id)
    
    if not task_list or task_list.user_id != user.id or not task_list.is_active:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    list_id = task.list_id
    await TaskCRUD.delete(session, task_id)
    
    text = """
✅ <b>Задача удалена</b>

Задача успешно удалена из списка.
"""
    
    await callback.message.edit_text(
        text=text,
        reply_markup=list_details_keyboard(list_id)
    )
    await callback.answer("Задача удалена")


@router.message(SetTaskNotificationStates.waiting_for_time)
async def set_task_notification_finish(message: Message, session: AsyncSession, state: FSMContext, user: User):
    """Завершить настройку уведомления для задачи"""
    time_text = (message.text or "").strip()
    
    # Валидация формата времени
    try:
        hours, minutes = time_text.split(":")
        hours = int(hours)
        minutes = int(minutes)
        
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError
        
        time_formatted = f"{hours:02d}:{minutes:02d}"
    except:
        await message.answer("❌ Неверный формат времени. Используйте формат HH:MM (например, 09:00)")
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    task_id = data.get("task_id")
    
    if not user.is_premium or not await get_owned_task(session, task_id, user):
        await message.answer("❌ Задача недоступна для настройки уведомления")
        await state.clear()
        return

    # Обновляем время уведомления
    task = await TaskCRUD.update_notification(session, task_id, time_formatted)
    
    text = f"""
✅ <b>Уведомление для задачи настроено!</b>

Вы будете получать уведомление в {time_formatted}

📌 Задача: {task.text[:100]}
"""
    
    await message.answer(
        text=text,
        reply_markup=task_keyboard(task_id, task.list_id, task.is_completed, True)
    )
    await state.clear()
