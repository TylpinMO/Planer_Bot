"""Обработчики базовых команд"""
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from bot.keyboards.inline import main_menu_keyboard, back_to_menu_keyboard, timezone_keyboard, profile_keyboard
from bot.utils.datetime_helpers import utc_now
from config import config

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, user: User):
    """Обработчик команды /start"""
    tz_sign = '+' if user.timezone_offset >= 0 else ''
    
    premium_status = '🆓 Бесплатный'
    if user.is_premium:
        if user.premium_until:
            from datetime import datetime
            days_left = (user.premium_until - datetime.utcnow()).days
            premium_status = f'👑 Премиум до {user.premium_until.strftime("%d.%m.%Y")} ({days_left} дн.)'
        else:
            premium_status = '👑 Премиум ♮️'
    
    welcome_text = f"""
👋 <b>Привет, {message.from_user.first_name}!</b>

Я помогу организовать задачи и напомню о важном.

<b>Твой статус:</b> {premium_status}
<b>Часовой пояс:</b> UTC{tz_sign}{user.timezone_offset}

📝 <b>Быстрый старт:</b>

1️⃣ <b>Создай список задач</b>
   ➕ Создать список → Введи название

2️⃣ <b>Добавь задачи</b>
   📋 Мои списки → Выбери список → ➕ Добавить задачу

3️⃣ <b>Настрой уведомления</b>
   В списке нажми 🔔 Настроить уведомление

4️⃣ <b>Проверь часовой пояс</b>
   👤 Профиль → ⏰ Часовой пояс

💡 <b>Премиум бонусы:</b>
• До 10 списков
• Уведомления для каждой задачи
• Ежедневная сводка

Используй кнопки ниже 👇
"""
    
    is_admin = message.from_user.id in config.ADMIN_IDS
    await message.answer(
        text=welcome_text,
        reply_markup=main_menu_keyboard(user.is_premium, is_admin)
    )


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery, user: User):
    """Показать главное меню"""
    tz_sign = '+' if user.timezone_offset >= 0 else ''
    
    premium_status = '🆓 Бесплатный'
    if user.is_premium:
        if user.premium_until:
            from datetime import datetime
            days_left = (user.premium_until - datetime.utcnow()).days
            premium_status = f'👑 Премиум до {user.premium_until.strftime("%d.%m.%Y")} ({days_left} дн.)'
        else:
            premium_status = '👑 Премиум ♮️'
    
    menu_text = f"""
🏠 <b>Главное меню</b>

<b>Статус:</b> {premium_status}
<b>Часовой пояс:</b> UTC{tz_sign}{user.timezone_offset}

<i>Уведомления будут приходить по вашему местному времени</i>
"""
    
    is_admin = callback.from_user.id in config.ADMIN_IDS
    try:
        await callback.message.edit_text(
            text=menu_text,
            reply_markup=main_menu_keyboard(user.is_premium, is_admin)
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            text=menu_text,
            reply_markup=main_menu_keyboard(user.is_premium, is_admin)
        )
    await callback.answer()


@router.callback_query(F.data == "set_timezone")
async def show_timezone_settings(callback: CallbackQuery, user: User):
    """Показать настройки часового пояса"""
    tz_sign = '+' if user.timezone_offset >= 0 else ''
    text = f"""
⏰ <b>Настройка часового пояса</b>

<b>Текущий часовой пояс:</b> UTC{tz_sign}{user.timezone_offset}

Выберите ваш часовой пояс из списка ниже.
Уведомления будут приходить по вашему местному времени.

<i>💡 Например, если вы установите уведомление на 09:00,
оно придёт в 09:00 по времени выбранного часового пояса</i>
"""
    
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=timezone_keyboard(user.timezone_offset)
        )
    except Exception:
        # Если не удалось отредактировать, удаляем старое и отправляем новое
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            text=text,
            reply_markup=timezone_keyboard(user.timezone_offset)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("tz_"))
async def set_timezone(callback: CallbackQuery, user: User, session: AsyncSession):
    """Установить часовой пояс"""
    from database.crud import UserCRUD
    
    offset = int(callback.data.split("_")[1])
    
    await UserCRUD.update_timezone(session, user.id, offset)
    
    tz_sign = '+' if offset >= 0 else ''
    await callback.answer(
        f"✅ Часовой пояс установлен: UTC{tz_sign}{offset}",
        show_alert=True
    )
    
    # Обновляем пользователя в памяти
    user.timezone_offset = offset
    
    # Возвращаемся в профиль
    await show_profile(callback, user, session)


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery, user: User, session: AsyncSession):
    """Показать профиль пользователя"""
    from database.crud import TaskListCRUD, TaskCRUD
    
    # Получаем статистику
    lists = await TaskListCRUD.get_user_lists(session, user.id)
    total_tasks = 0
    completed_tasks = 0
    
    for task_list in lists:
        tasks = await TaskCRUD.get_list_tasks(session, task_list.id, include_completed=True)
        total_tasks += len(tasks)
        completed_tasks += len([t for t in tasks if t.is_completed])
    
    # Часовой пояс
    tz_text = f"UTC{user.timezone_offset:+d}"
    
    # Ежедневная сводка
    summary_text = user.daily_summary_time if user.daily_summary_time else "не настроена"
    
    text = f"""
👤 <b>Ваш профиль</b>

<b>📊 Статистика:</b>
• Списков: {len(lists)}
• Всего задач: {total_tasks}
• Выполнено: {completed_tasks}

<b>⚙️ Настройки:</b>
• Часовой пояс: {tz_text}
"""
    
    if user.is_premium:
        text += f"• Ежедневная сводка: {summary_text}\n"
    
    text += "\n<i>Выберите настройку для изменения:</i>"
    
    await callback.message.edit_text(
        text=text,
        reply_markup=profile_keyboard(user.is_premium)
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    """Показать справку"""
    help_text = """
ℹ️ <b>Полное руководство по боту</b>

📋 <b>СПИСКИ И ЗАДАЧИ</b>

• Создайте список задач (например: "Работа", "Дом")
• Добавляйте задачи в список
• Отмечайте выполненные задачи
• Просматривайте историю выполненных

🔔 <b>УВЕДОМЛЕНИЯ</b>

<b>Бесплатный тариф:</b>
• 1 список задач
• 1 уведомление на список в выбранное время

<b>Премиум тариф:</b>
• До 10 списков
• Кастомные уведомления для каждой задачи
• Ежедневная сводка со всеми задачами

📊 <b>КАК НАСТРОИТЬ УВЕДОМЛЕНИЯ</b>

<b>Уведомление по списку:</b>
Мои списки → Выбрать список → 🔔 Настроить уведомление

<b>Для задачи (премиум):</b>
При создании задачи или через карточку задачи

<b>Ежедневная сводка (премиум):</b>
Профиль → 📊 Ежедневная сводка

⚙️ <b>НАСТРОЙКИ</b>

• Часовой пояс: Профиль → ⏰ Часовой пояс
• Статистика и настройки: Профиль

⭐ <b>ПРЕМИУМ</b>
Всего 250 звёзд Telegram

<b>Команды:</b>
/start - Главное меню
"""
    
    await callback.message.edit_text(
        text=help_text,
        reply_markup=back_to_menu_keyboard()
    )
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
ℹ️ <b>Справка по использованию</b>

<b>Основные возможности:</b>

📋 <b>Списки задач</b>
• Создавайте списки для разных целей
• Организуйте задачи по спискам
• Настраивайте уведомления

✅ <b>Задачи</b>
• Добавляйте неограниченное количество задач
• Отмечайте выполненные
• Устанавливайте приоритеты

🔔 <b>Уведомления</b>
• Бесплатно: 1 уведомление на весь список
• Премиум: индивидуальные уведомления для каждой задачи

⭐ <b>Премиум</b>
• 10 списков вместо 1
• Кастомные уведомления
• Всего 250 звёзд

<b>Команды:</b>
/start - Главное меню
/help - Эта справка
"""
    
    await message.answer(
        text=help_text,
        reply_markup=back_to_menu_keyboard()
    )


@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    """Показать админ-панель"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    text = """
🛠 <b>Админ-панель</b>

<b>Доступные команды:</b>

📊 /stats - Полная статистика бота
👑 /give_premium USER_ID [DAYS] - Выдать премиум (по умолчанию 30 дней)
⏰ /extend_premium USER_ID DAYS - Продлить премиум
♾️ /give_premium_forever USER_ID - Бесконечная подписка
🔻 /remove_premium USER_ID - Убрать премиум
📋 /user_info USER_ID - Информация о пользователе

<b>Примеры:</b>
<code>/give_premium 123456789</code> - выдать на 30 дней
<code>/give_premium 123456789 60</code> - выдать на 60 дней
<code>/extend_premium 123456789 30</code> - продлить на 30 дней
<code>/give_premium_forever 123456789</code> - навсегда ♾️
<code>/remove_premium 123456789</code>
<code>/user_info 123456789</code>

💡 <b>Узнать свой Telegram ID:</b>
Напишите @userinfobot
"""
    
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=back_to_menu_keyboard()
        )
    except Exception:
        pass
    await callback.answer()
