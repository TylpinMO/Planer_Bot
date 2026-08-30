"""Обработчики для работы со списками задач"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.crud import TaskListCRUD, TaskCRUD
from bot.keyboards.inline import (
    lists_keyboard,
    list_details_keyboard,
    tasks_list_keyboard,
    confirm_delete_keyboard,
    back_to_menu_keyboard,
    cancel_keyboard,
    main_menu_keyboard
)
from config import config

router = Router()


class CreateListStates(StatesGroup):
    """Состояния для создания списка"""
    waiting_for_name = State()


class SetNotificationStates(StatesGroup):
    """Состояния для настройки уведомления"""
    waiting_for_time = State()


@router.callback_query(F.data == "my_lists")
async def show_lists(callback: CallbackQuery, session: AsyncSession, user: User):
    """Показать списки задач пользователя"""
    lists = await TaskListCRUD.get_user_lists(session, user.id)
    
    if not lists:
        text = """
📋 <b>У вас пока нет списков задач</b>

Создайте свой первый список, чтобы начать планировать задачи!
"""
        await callback.message.edit_text(
            text=text,
            reply_markup=back_to_menu_keyboard()
        )
    else:
        text = f"""
📋 <b>Ваши списки задач</b>

Всего списков: {len(lists)}
{'(максимум 10)' if user.is_premium else '(максимум 1)'}

Выберите список:
"""
        await callback.message.edit_text(
            text=text,
            reply_markup=lists_keyboard(lists, page=0)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("lists_page_"))
async def show_lists_page(callback: CallbackQuery, session: AsyncSession, user: User):
    """Показать страницу списков"""
    page = int(callback.data.split("_")[2])
    lists = await TaskListCRUD.get_user_lists(session, user.id)
    
    text = f"""
📋 <b>Ваши списки задач</b>

Всего списков: {len(lists)}
{'(максимум 10)' if user.is_premium else '(максимум 1)'}

Выберите список:
"""
    await callback.message.edit_text(
        text=text,
        reply_markup=lists_keyboard(lists, page=page)
    )
    await callback.answer()


@router.callback_query(F.data == "create_list")
async def create_list_start(callback: CallbackQuery, session: AsyncSession, user: User, state: FSMContext):
    """Начать создание списка"""
    # Проверяем лимит
    count = await TaskListCRUD.count_user_lists(session, user.id)
    limit = config.PREMIUM_LISTS_LIMIT if user.is_premium else config.FREE_LISTS_LIMIT
    
    if count >= limit:
        text = f"""
❌ <b>Достигнут лимит списков</b>

Ваш лимит: {limit} {'списков' if user.is_premium else 'список'}

{'Удалите ненужные списки или обновите тариф.' if user.is_premium else '⭐ Купите Премиум, чтобы создать до 10 списков!'}
"""
        await callback.message.edit_text(
            text=text,
            reply_markup=back_to_menu_keyboard()
        )
        await callback.answer("Достигнут лимит!", show_alert=True)
        return
    
    text = """
✏️ <b>Создание нового списка</b>

Введите название для списка задач:

Например: "Работа", "Покупки", "Учёба"
"""
    
    await callback.message.edit_text(
        text=text,
        reply_markup=cancel_keyboard()
    )
    await state.set_state(CreateListStates.waiting_for_name)
    await callback.answer()


@router.message(CreateListStates.waiting_for_name)
async def create_list_finish(message: Message, session: AsyncSession, user: User, state: FSMContext):
    """Завершить создание списка"""
    list_name = message.text.strip()
    
    if len(list_name) > 255:
        await message.answer("❌ Название слишком длинное. Максимум 255 символов.")
        return
    
    if len(list_name) < 1:
        await message.answer("❌ Название не может быть пустым.")
        return
    
    # Создаем список
    task_list = await TaskListCRUD.create(session, user.id, list_name)
    
    text = f"""
✅ <b>Список создан!</b>

📝 {task_list.name}

Теперь вы можете добавлять задачи в этот список.
"""
    
    await message.answer(
        text=text,
        reply_markup=list_details_keyboard(task_list.id)
    )
    await state.clear()


@router.callback_query(F.data.startswith("list_"))
async def show_list_details(callback: CallbackQuery, session: AsyncSession, user: User):
    """Показать детали списка"""
    list_id = int(callback.data.split("_")[1])
    task_list = await TaskListCRUD.get_by_id(session, list_id)
    
    if not task_list or task_list.user_id != user.id:
        await callback.answer("❌ Список не найден", show_alert=True)
        return
    
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

{'<i>Список пуст. Добавьте первую задачу!</i>' if not tasks else '<b>Нажмите на задачу, чтобы отметить её выполненной:</b>'}
"""
    
    # Показываем кнопки для всех задач (используем клавиатуру)
    try:
        if tasks:
            await callback.message.edit_text(
                text=text,
                reply_markup=tasks_list_keyboard(tasks, list_id, task_list.notification_time is not None)
            )
        else:
            await callback.message.edit_text(
                text=text,
                reply_markup=list_details_keyboard(list_id, task_list.notification_time is not None)
            )
    except Exception:
        # Игнорируем ошибку, если сообщение не изменилось
        pass
    
    await callback.answer()


@router.callback_query(F.data.startswith("completed_tasks_"))
async def show_completed_tasks(callback: CallbackQuery, session: AsyncSession, user: User):
    """Показать историю выполненных задач"""
    list_id = int(callback.data.split("_")[2])
    
    task_list = await TaskListCRUD.get_by_id(session, list_id)
    
    if not task_list or task_list.user_id != user.id:
        await callback.answer("❌ Список не найден", show_alert=True)
        return
    
    all_tasks = await TaskCRUD.get_list_tasks(session, list_id, include_completed=True)
    completed_tasks = [t for t in all_tasks if t.is_completed]
    
    if not completed_tasks:
        text = f"""
📜 <b>История выполненных задач</b>

📋 Список: {task_list.name}

<i>Пока нет выполненных задач</i>
"""
        await callback.message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад к списку", callback_data=f"list_{list_id}")]
            ])
        )
    else:
        # Сортируем по дате выполнения (новые сначала)
        completed_tasks.sort(key=lambda x: x.completed_at if x.completed_at else x.created_at, reverse=True)
        
        text = f"""
📜 <b>История выполненных задач</b>

📋 Список: {task_list.name}
Всего выполнено: {len(completed_tasks)}

"""
        
        for i, task in enumerate(completed_tasks[:20], 1):
            completed_date = task.completed_at.strftime('%d.%m.%Y') if task.completed_at else 'Дата неизвестна'
            text += f"\n{i}. ✅ {task.text[:40]}"
            if len(task.text) > 40:
                text += "..."
            text += f"\n   <i>{completed_date}</i>"
        
        if len(completed_tasks) > 20:
            text += f"\n\n<i>... и ещё {len(completed_tasks) - 20} задач</i>"
        
        await callback.message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад к списку", callback_data=f"list_{list_id}")]
            ])
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("delete_list_"))
async def delete_list_confirm(callback: CallbackQuery):
    """Подтверждение удаления списка"""
    list_id = int(callback.data.split("_")[2])
    
    text = """
⚠️ <b>Подтверждение удаления</b>

Вы уверены, что хотите удалить этот список?

Все задачи в нём будут также удалены.
"""
    
    await callback.message.edit_text(
        text=text,
        reply_markup=confirm_delete_keyboard("list", list_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_list_"))
async def delete_list_confirmed(callback: CallbackQuery, session: AsyncSession, user: User):
    """Удалить список после подтверждения"""
    list_id = int(callback.data.split("_")[3])
    
    task_list = await TaskListCRUD.get_by_id(session, list_id)
    
    if not task_list or task_list.user_id != user.id:
        await callback.answer("❌ Список не найден", show_alert=True)
        return
    
    await TaskListCRUD.delete(session, list_id)
    
    text = """
✅ <b>Список удалён</b>

Список и все его задачи успешно удалены.
"""
    
    is_admin = callback.from_user.id in config.ADMIN_IDS
    await callback.message.edit_text(
        text=text,
        reply_markup=main_menu_keyboard(user.is_premium, is_admin)
    )
    await callback.answer("Список удалён")


@router.callback_query(F.data.startswith("clear_list_"))
async def clear_list_confirm(callback: CallbackQuery):
    """Подтверждение очистки списка"""
    list_id = int(callback.data.split("_")[2])
    
    text = """
⚠️ <b>Подтверждение очистки</b>

Вы уверены, что хотите очистить этот список?

Все задачи в нём будут удалены, но сам список останется.
"""
    
    await callback.message.edit_text(
        text=text,
        reply_markup=confirm_delete_keyboard("clear", list_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_clear_"))
async def clear_list_confirmed(callback: CallbackQuery, session: AsyncSession, user: User):
    """Очистить список после подтверждения"""
    list_id = int(callback.data.split("_")[3])
    
    task_list = await TaskListCRUD.get_by_id(session, list_id)
    
    if not task_list or task_list.user_id != user.id:
        await callback.answer("❌ Список не найден", show_alert=True)
        return
    
    # Удаляем все задачи из списка
    tasks = await TaskCRUD.get_list_tasks(session, list_id, include_completed=True)
    for task in tasks:
        await TaskCRUD.delete(session, task.id)
    
    text = f"""
✅ <b>Список очищен</b>

Все задачи удалены из списка "{task_list.name}".
"""
    
    await callback.message.edit_text(
        text=text,
        reply_markup=list_details_keyboard(list_id, task_list.notification_time is not None)
    )
    await callback.answer("Список очищен")


@router.callback_query(F.data.startswith("cancel_delete_"))
async def cancel_delete(callback: CallbackQuery, session: AsyncSession, user: User):
    """Отменить удаление"""
    parts = callback.data.split("_")
    item_type = parts[2]
    item_id = int(parts[3])
    
    if item_type == "list" or item_type == "clear":
        # Возвращаемся к просмотру списка
        list_id = item_id
        task_list = await TaskListCRUD.get_by_id(session, list_id)
        
        if task_list and task_list.user_id == user.id:
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

{'<i>Список пуст. Добавьте первую задачу!</i>' if not tasks else '<b>Нажмите на задачу, чтобы отметить её выполненной:</b>'}
"""
            
            if tasks:
                await callback.message.edit_text(
                    text=text,
                    reply_markup=tasks_list_keyboard(tasks, list_id, task_list.notification_time is not None)
                )
            else:
                await callback.message.edit_text(
                    text=text,
                    reply_markup=list_details_keyboard(list_id, task_list.notification_time is not None)
                )
    elif item_type == "task":
        # Для задачи возвращаемся к её просмотру (если потребуется)
        pass
    
    await callback.answer("Отменено")


@router.callback_query(F.data.startswith("set_notification_"))
async def set_notification_start(callback: CallbackQuery, user: User, state: FSMContext, session: AsyncSession):
    """Начать настройку уведомления"""
    list_id = int(callback.data.split("_")[2])
    
    task_list = await TaskListCRUD.get_by_id(session, list_id)
    if not task_list or task_list.user_id != user.id or not task_list.is_active:
        await callback.answer("❌ Список не найден", show_alert=True)
        return

    text = f"""
🔔 <b>Настройка уведомления</b>

{'<b>Премиум функция:</b> Вы можете настроить время ежедневного уведомления для этого списка.' if user.is_premium else '<b>Бесплатная версия:</b> Доступно 1 уведомление на весь список.'}

Введите время в формате <b>HH:MM</b>

Например: 09:00 или 18:30
"""
    
    await callback.message.edit_text(
        text=text,
        reply_markup=cancel_keyboard()
    )
    await state.set_state(SetNotificationStates.waiting_for_time)
    await state.update_data(list_id=list_id)
    await callback.answer()


@router.message(SetNotificationStates.waiting_for_time)
async def set_notification_finish(message: Message, session: AsyncSession, state: FSMContext, user: User):
    """Завершить настройку уведомления"""
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
    list_id = data.get("list_id")
    
    task_list = await TaskListCRUD.get_by_id(session, list_id)
    if not task_list or task_list.user_id != user.id or not task_list.is_active:
        await message.answer("❌ Список не найден")
        await state.clear()
        return

    # Обновляем время уведомления
    task_list = await TaskListCRUD.update_notification_time(session, list_id, time_formatted)
    
    text = f"""
✅ <b>Уведомление настроено!</b>

Вы будете получать ежедневное уведомление в {time_formatted}

📝 Список: {task_list.name}
"""
    
    await message.answer(
        text=text,
        reply_markup=list_details_keyboard(list_id, True)
    )
    await state.clear()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext, user: User):
    """Отменить текущее действие"""
    await state.clear()
    
    await callback.message.edit_text(
        text="❌ Действие отменено",
        reply_markup=main_menu_keyboard(user.is_premium)
    )
    await callback.answer("Отменено")
