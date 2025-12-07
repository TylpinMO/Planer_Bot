"""Клавиатуры для бота"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config


def main_menu_keyboard(is_premium: bool = False, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📋 Мои списки", callback_data="my_lists")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Создать список", callback_data="create_list")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile")
    )
    
    if not is_premium:
        builder.row(
            InlineKeyboardButton(text="⭐ Купить премиум", callback_data="premium_info")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="👑 Мой премиум", callback_data="premium_status")
        )
        builder.row(
            InlineKeyboardButton(text="⭐ Продлить премиум", callback_data="premium_info")
        )
    
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="🛠 Админ-панель", callback_data="admin_panel")
        )
    
    builder.row(
        InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")
    )
    
    return builder.as_markup()


def lists_keyboard(lists: list, page: int = 0, items_per_page: int = 5) -> InlineKeyboardMarkup:
    """Клавиатура со списками задач"""
    builder = InlineKeyboardBuilder()
    
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_lists = lists[start_idx:end_idx]
    
    for task_list in page_lists:
        task_count = len([t for t in task_list.tasks if not t.is_completed])
        builder.row(
            InlineKeyboardButton(
                text=f"📝 {task_list.name} ({task_count})",
                callback_data=f"list_{task_list.id}"
            )
        )
    
    # Пагинация
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"lists_page_{page-1}")
        )
    if end_idx < len(lists):
        navigation_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"lists_page_{page+1}")
        )
    
    if navigation_buttons:
        builder.row(*navigation_buttons)
    
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    )
    
    return builder.as_markup()


def list_details_keyboard(list_id: int, has_notification: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра списка"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="➕ Добавить задачу", callback_data=f"add_task_{list_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📜 История выполненных", callback_data=f"completed_tasks_{list_id}")
    )
    builder.row(
        InlineKeyboardButton(
            text=f"🔔 {'Изменить' if has_notification else 'Настроить'} уведомление",
            callback_data=f"set_notification_{list_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить список", callback_data=f"delete_list_{list_id}"),
        InlineKeyboardButton(text="📋 Все списки", callback_data="my_lists")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    )
    
    return builder.as_markup()


def task_keyboard(task_id: int, list_id: int, is_completed: bool = False, is_premium: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для управления задачей"""
    builder = InlineKeyboardBuilder()
    
    status_text = "✅ Выполнено" if is_completed else "☑️ Отметить выполненной"
    builder.row(
        InlineKeyboardButton(text=status_text, callback_data=f"toggle_task_{task_id}")
    )
    
    if is_premium:
        builder.row(
            InlineKeyboardButton(text="🔔 Уведомление", callback_data=f"task_notify_{task_id}")
        )
    
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_task_{task_id}"),
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"list_{list_id}")
    )
    
    return builder.as_markup()


def tasks_list_keyboard(tasks: list, list_id: int, has_notification: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура со списком задач"""
    builder = InlineKeyboardBuilder()
    
    for task in tasks:
        status = "✅" if task.is_completed else "⬜"
        priority_emoji = {0: "", 1: "🔸", 2: "🔴"}
        text = f"{status} {priority_emoji.get(task.priority, '')} {task.text[:40]}"
        
        builder.row(
            InlineKeyboardButton(text=text, callback_data=f"task_{task.id}")
        )
    
    builder.row(
        InlineKeyboardButton(text="➕ Добавить задачу", callback_data=f"add_task_{list_id}")
    )
    builder.row(
        InlineKeyboardButton(
            text=f"🔔 {'Изменить' if has_notification else 'Настроить'} уведомление",
            callback_data=f"set_notification_{list_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить список", callback_data=f"delete_list_{list_id}"),
        InlineKeyboardButton(text="🧹 Очистить список", callback_data=f"clear_list_{list_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Все списки", callback_data="my_lists"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    )
    
    return builder.as_markup()


def confirm_delete_keyboard(item_type: str, item_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{item_type}_{item_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_delete_{item_type}_{item_id}")
    )
    
    return builder.as_markup()


def premium_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для покупки премиума"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="⭐ Купить Премиум (250 звёзд)", callback_data="buy_premium")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    )
    
    return builder.as_markup()


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура возврата в меню"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    )
    
    return builder.as_markup()


def profile_keyboard(is_premium: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура профиля"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="⏰ Часовой пояс", callback_data="set_timezone")
    )
    
    if is_premium:
        builder.row(
            InlineKeyboardButton(text="📊 Ежедневная сводка", callback_data="set_daily_summary")
        )
    
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    )
    
    return builder.as_markup()


def back_to_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура возврата в профиль"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    )
    
    return builder.as_markup()


def premium_status_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура в статусе премиума"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📊 Настроить ежедневную сводку", callback_data="set_daily_summary")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    )
    
    return builder.as_markup()


def timezone_keyboard(current_offset: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора часового пояса"""
    builder = InlineKeyboardBuilder()
    
    # Популярные часовые пояса
    timezones = [
        (-12, "UTC-12 🌐"),
        (-11, "UTC-11 🌐"),
        (-10, "UTC-10 (Гавайи) 🏝"),
        (-9, "UTC-9 (Аляска) ❄️"),
        (-8, "UTC-8 (Лос-Анджелес) 🌴"),
        (-7, "UTC-7 (Денвер) 🏔"),
        (-6, "UTC-6 (Чикаго) 🌆"),
        (-5, "UTC-5 (Нью-Йорк) 🗽"),
        (-4, "UTC-4 🌐"),
        (-3, "UTC-3 (Бразилия) 🇧🇷"),
        (-2, "UTC-2 🌐"),
        (-1, "UTC-1 🌐"),
        (0, "UTC+0 (Лондон) 🇬🇧"),
        (1, "UTC+1 (Берлин) 🇩🇪"),
        (2, "UTC+2 (Киев) 🇺🇦"),
        (3, "UTC+3 (Москва) 🇷🇺"),
        (4, "UTC+4 (Дубай) 🇦🇪"),
        (5, "UTC+5 (Карачи) 🇵🇰"),
        (6, "UTC+6 (Алматы) 🇰🇿"),
        (7, "UTC+7 (Бангкок) 🇹🇭"),
        (8, "UTC+8 (Пекин) 🇨🇳"),
        (9, "UTC+9 (Токио) 🇯🇵"),
        (10, "UTC+10 (Сидней) 🇦🇺"),
        (11, "UTC+11 🌐"),
        (12, "UTC+12 (Окленд) 🇳🇿"),
        (13, "UTC+13 🌐"),
        (14, "UTC+14 🌐"),
    ]
    
    for offset, label in timezones:
        prefix = "✅ " if offset == current_offset else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{prefix}{label}",
                callback_data=f"tz_{offset}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()


def premium_renew_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для продления премиума"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="⭐ Продлить премиум", callback_data="premium_info")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    )
    
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    
    return builder.as_markup()
