"""Обработчики админских команд"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.crud import UserCRUD, PaymentCRUD, TaskListCRUD
from bot.keyboards.inline import back_to_menu_keyboard
from config import config

router = Router()


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    return user_id in config.ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Админ панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ панели.")
        return
    
    text = """
🛠 <b>Админ панель</b>

<b>Доступные команды:</b>

📊 /stats - Статистика
👑 /give_premium USER_ID [DAYS] - Выдать премиум (по умолчанию 30 дней)
⏰ /extend_premium USER_ID DAYS - Продлить премиум
♾️ /give_premium_forever USER_ID - Бесконечная подписка
🔻 /remove_premium USER_ID - Убрать премиум
📋 /user_info USER_ID - Информация о пользователе

<b>Примеры:</b>
<code>/give_premium 123456789</code>
<code>/give_premium 123456789 60</code>
<code>/extend_premium 123456789 30</code>
<code>/give_premium_forever 123456789</code>
<code>/remove_premium 123456789</code>
<code>/user_info 123456789</code>
"""
    
    await message.answer(text)


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    """Статистика"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    # Получаем статистику пользователей
    user_stats = await UserCRUD.get_stats(session)
    
    # Получаем статистику платежей
    payment_stats = await PaymentCRUD.get_stats(session)
    
    # Получаем премиум пользователей
    premium_users = await UserCRUD.get_premium_users(session)
    
    # Подсчитываем общее количество списков
    all_users = await UserCRUD.get_all_users(session)
    total_lists = 0
    for user in all_users:
        count = await TaskListCRUD.count_user_lists(session, user.id)
        total_lists += count
    
    text = f"""
📊 <b>Статистика бота</b>

👥 <b>Пользователи:</b>
• Всего: {user_stats['total']}
• Премиум: {user_stats['premium']}
• Бесплатных: {user_stats['free']}

💰 <b>Платежи:</b>
• Всего платежей: {payment_stats['total_payments']}
• Всего звёзд: {payment_stats['total_stars']} ⭐

📋 <b>Контент:</b>
• Всего списков: {total_lists}

👑 <b>Активные премиум пользователи:</b>
"""
    
    if premium_users:
        for user in premium_users[:10]:
            username = f"@{user.username}" if user.username else user.first_name or "Без имени"
            days_left = 0
            if user.premium_until:
                from datetime import datetime
                days_left = (user.premium_until - datetime.utcnow()).days
            text += f"\n• {username} (ID: {user.telegram_id}) - осталось {days_left} дней"
        
        if len(premium_users) > 10:
            text += f"\n\n<i>... и ещё {len(premium_users) - 10} пользователей</i>"
    else:
        text += "\n<i>Нет премиум пользователей</i>"
    
    await message.answer(text)


@router.message(Command("give_premium"))
async def cmd_give_premium(message: Message, session: AsyncSession):
    """Выдать премиум пользователю"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    # Парсим команду
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Использование: /give_premium USER_ID [DAYS]\n\nПример: /give_premium 123456789 30")
        return
    
    try:
        user_telegram_id = int(parts[1])
        days = int(parts[2]) if len(parts) > 2 else 30
    except ValueError:
        await message.answer("❌ Неверный формат. USER_ID и DAYS должны быть числами.")
        return
    
    # Находим пользователя
    user = await UserCRUD.get_by_telegram_id(session, user_telegram_id)
    
    if not user:
        await message.answer(f"❌ Пользователь с ID {user_telegram_id} не найден.")
        return
    
    # Выдаём премиум
    await UserCRUD.set_premium(session, user.id, days)
    
    # Создаём подписку (без платежа)
    from database.crud import SubscriptionCRUD
    await SubscriptionCRUD.create(session, user.id, payment_id=None, days=days)
    
    username = f"@{user.username}" if user.username else user.first_name or "Без имени"
    
    text = f"""
✅ <b>Премиум выдан!</b>

Пользователь: {username}
ID: {user.telegram_id}
Срок: {days} дней

Премиум успешно активирован.
"""
    
    await message.answer(text)
    
    # Уведомляем пользователя
    try:
        await message.bot.send_message(
            chat_id=user.telegram_id,
            text=f"""
🎉 <b>Вам выдан премиум!</b>

Администратор активировал для вас премиум подписку на {days} дней.

<b>Теперь вам доступно:</b>
📋 До 10 списков задач
🔔 Кастомные уведомления для каждой задачи
⚡ Приоритетная поддержка

Приятного использования! ✨
"""
        )
    except:
        pass


@router.message(Command("remove_premium"))
async def cmd_remove_premium(message: Message, session: AsyncSession):
    """Убрать премиум у пользователя"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    # Парсим команду
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Использование: /remove_premium USER_ID\n\nПример: /remove_premium 123456789")
        return
    
    try:
        user_telegram_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный формат. USER_ID должен быть числом.")
        return
    
    # Находим пользователя
    user = await UserCRUD.get_by_telegram_id(session, user_telegram_id)
    
    if not user:
        await message.answer(f"❌ Пользователь с ID {user_telegram_id} не найден.")
        return
    
    if not user.is_premium:
        await message.answer(f"ℹ️ У пользователя и так нет премиума.")
        return
    
    # Убираем премиум
    await UserCRUD.remove_premium(session, user.id)
    
    username = f"@{user.username}" if user.username else user.first_name or "Без имени"
    
    text = f"""
✅ <b>Премиум удалён!</b>

Пользователь: {username}
ID: {user.telegram_id}

Премиум статус успешно удалён.
"""
    
    await message.answer(text)
    
    # Уведомляем пользователя
    try:
        await message.bot.send_message(
            chat_id=user.telegram_id,
            text="""
ℹ️ <b>Ваш премиум статус истёк</b>

Ваша премиум подписка была деактивирована.

Теперь вам доступно:
📋 1 список задач
🔔 1 уведомление на весь список

Чтобы снова получить премиум возможности, используйте команду /start и выберите "⭐ Премиум".
"""
        )
    except:
        pass


@router.message(Command("user_info"))
async def cmd_user_info(message: Message, session: AsyncSession):
    """Информация о пользователе"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    # Парсим команду
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Использование: /user_info USER_ID\n\nПример: /user_info 123456789")
        return
    
    try:
        user_telegram_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный формат. USER_ID должен быть числом.")
        return
    
    # Находим пользователя
    user = await UserCRUD.get_by_telegram_id(session, user_telegram_id)
    
    if not user:
        await message.answer(f"❌ Пользователь с ID {user_telegram_id} не найден.")
        return
    
    # Получаем информацию
    lists_count = await TaskListCRUD.count_user_lists(session, user.id)
    
    from database.crud import SubscriptionCRUD, PaymentCRUD
    subscriptions = await SubscriptionCRUD.get_user_subscriptions(session, user.id)
    
    username = f"@{user.username}" if user.username else "Не указан"
    name = user.first_name or "Не указано"
    status = "👑 Премиум" if user.is_premium else "🆓 Бесплатный"
    
    text = f"""
👤 <b>Информация о пользователе</b>

<b>Основное:</b>
• Имя: {name}
• Username: {username}
• ID: {user.telegram_id}
• Статус: {status}

<b>Активность:</b>
• Списков задач: {lists_count}
• Дата регистрации: {user.created_at.strftime('%d.%m.%Y %H:%M')}
"""
    
    if user.is_premium and user.premium_until:
        from datetime import datetime
        days_left = (user.premium_until - datetime.utcnow()).days
        text += f"\n<b>Премиум:</b>\n• Активен до: {user.premium_until.strftime('%d.%m.%Y')}\n• Осталось дней: {days_left}"
    elif user.is_premium and not user.premium_until:
        text += f"\n<b>Премиум:</b>\n• ♾️ Бесконечная подписка"
    
    text += f"\n\n<b>Подписок:</b> {len(subscriptions)}"
    
    await message.answer(text)


@router.message(Command("extend_premium"))
async def cmd_extend_premium(message: Message, session: AsyncSession):
    """Продлить премиум пользователю"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    # Парсим команду
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("❌ Использование: /extend_premium USER_ID DAYS\n\nПример: /extend_premium 123456789 30")
        return
    
    try:
        user_telegram_id = int(parts[1])
        days = int(parts[2])
    except ValueError:
        await message.answer("❌ Неверный формат. USER_ID и DAYS должны быть числами.")
        return
    
    if days < 1:
        await message.answer("❌ Количество дней должно быть больше 0.")
        return
    
    # Находим пользователя
    user = await UserCRUD.get_by_telegram_id(session, user_telegram_id)
    
    if not user:
        await message.answer(f"❌ Пользователь с ID {user_telegram_id} не найден.")
        return
    
    # Продляем премиум
    from datetime import datetime, timedelta
    if user.premium_until and user.premium_until > datetime.utcnow():
        # Если премиум активен - продляем от текущей даты окончания
        new_date = user.premium_until + timedelta(days=days)
    else:
        # Если премиум неактивен - продляем от сегодня
        new_date = datetime.utcnow() + timedelta(days=days)
    
    user.is_premium = True
    user.premium_until = new_date
    user.premium_notified_3days = False
    user.premium_notified_2days = False
    user.premium_notified_1day = False
    
    await session.commit()
    
    username = f"@{user.username}" if user.username else user.first_name or f"ID {user.telegram_id}"
    await message.answer(
        f"✅ Премиум продлён!\n\n"
        f"👤 Пользователь: {username}\n"
        f"⏰ Добавлено дней: {days}\n"
        f"📅 Действует до: {new_date.strftime('%d.%m.%Y')}"
    )


@router.message(Command("give_premium_forever"))
async def cmd_give_premium_forever(message: Message, session: AsyncSession):
    """Выдать бесконечную премиум подписку"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    # Парсим команду
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Использование: /give_premium_forever USER_ID\n\nПример: /give_premium_forever 123456789")
        return
    
    try:
        user_telegram_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный формат. USER_ID должен быть числом.")
        return
    
    # Находим пользователя
    user = await UserCRUD.get_by_telegram_id(session, user_telegram_id)
    
    if not user:
        await message.answer(f"❌ Пользователь с ID {user_telegram_id} не найден.")
        return
    
    # Выдаём бесконечный премиум
    user.is_premium = True
    user.premium_until = None  # None = бесконечно
    user.premium_notified_3days = False
    user.premium_notified_2days = False
    user.premium_notified_1day = False
    
    await session.commit()
    
    username = f"@{user.username}" if user.username else user.first_name or f"ID {user.telegram_id}"
    await message.answer(
        f"✅ Бесконечная подписка выдана!\n\n"
        f"👤 Пользователь: {username}\n"
        f"♾️ Подписка бессрочная"
    )
