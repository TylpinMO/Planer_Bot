"""Обработчики для премиум подписки и платежей"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, PreCheckoutQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from database.models import User
from database.crud import UserCRUD, SubscriptionCRUD, PaymentCRUD
from bot.keyboards.inline import premium_keyboard, main_menu_keyboard, back_to_menu_keyboard, premium_status_keyboard, cancel_keyboard, back_to_profile_keyboard
from services.payments import PaymentService
from config import config

router = Router()


class SetDailySummaryStates(StatesGroup):
    """Состояния для настройки ежедневной сводки"""
    waiting_for_time = State()


@router.callback_query(F.data == "premium_info")
async def show_premium_info(callback: CallbackQuery, user: User):
    """Показать информацию о премиуме"""
    text = """
⭐ <b>Премиум подписка</b>

<b>Что вы получите:</b>

📋 <b>10 списков задач</b>
Вместо одного списка - целых 10!
Разделите задачи по темам, проектам, приоритетам.

🔔 <b>Кастомные уведомления</b>
Настраивайте уникальное время уведомления для каждой задачи.
Полный контроль над вашим расписанием!

⚡ <b>Приоритетная поддержка</b>
Быстрая помощь при возникновении вопросов.

💎 <b>Цена: всего 250 звёзд</b>
Подписка действует 30 дней.

<i>Звёзды Telegram - это внутренняя валюта Telegram.
Купить их можно в любом боте через меню платежей.</i>
"""
    
    await callback.message.edit_text(
        text=text,
        reply_markup=premium_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "premium_status")
async def show_premium_status(callback: CallbackQuery, user: User, session: AsyncSession):
    """Показать статус премиум подписки"""
    if not user.is_premium:
        await show_premium_info(callback, user)
        return
    
    subscription = await SubscriptionCRUD.get_active_subscription(session, user.id)
    
    days_left = 0
    if user.premium_until:
        days_left = (user.premium_until - datetime.utcnow()).days
    
    summary_info = ""
    if user.daily_summary_time:
        summary_info = f"\n📊 Ежедневная сводка: {user.daily_summary_time}"
    else:
        summary_info = "\n📊 Ежедневная сводка: не настроена"
    
    text = f"""
👑 <b>Премиум активен</b>

<b>Ваша подписка:</b>
• Статус: Активна ✅
• Осталось дней: {days_left}
• Действует до: {user.premium_until.strftime('%d.%m.%Y') if user.premium_until else 'Не указано'}{summary_info}

<b>Ваши преимущества:</b>
📋 До 10 списков задач
🔔 Кастомные уведомления для каждой задачи
📊 Ежедневная сводка по всем задачам
⚡ Приоритетная поддержка

Спасибо, что поддерживаете проект! 💙
"""
    
    await callback.message.edit_text(
        text=text,
        reply_markup=premium_status_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "buy_premium")
async def buy_premium(callback: CallbackQuery, user: User):
    """Инициировать покупку премиума"""
    if user.is_premium:
        await callback.answer("У вас уже есть активная премиум подписка!", show_alert=True)
        return
    
    # Получаем данные для инвойса
    invoice_data = PaymentService.get_premium_invoice_data()
    
    # Отправляем инвойс
    await callback.message.answer_invoice(
        **invoice_data,
        provider_token=""  # Пустой для Telegram Stars
    )
    
    await callback.answer("Счёт на оплату отправлен!")


@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """Обработка pre-checkout запроса"""
    # Валидация платежа
    is_valid = PaymentService.validate_payment(
        pre_checkout_query.invoice_payload,
        pre_checkout_query.total_amount
    )
    
    if is_valid:
        await pre_checkout_query.answer(ok=True)
    else:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Произошла ошибка при обработке платежа. Попробуйте снова."
        )


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, session: AsyncSession, user: User):
    """Обработка успешного платежа"""
    payment_info = message.successful_payment
    
    # Сохраняем платёж в БД
    payment = await PaymentCRUD.create(
        session=session,
        user_id=user.id,
        telegram_payment_charge_id=payment_info.telegram_payment_charge_id,
        amount_stars=payment_info.total_amount
    )
    
    # Активируем премиум
    await UserCRUD.set_premium(session, user.id, days=30)
    
    # Создаём подписку
    await SubscriptionCRUD.create(
        session=session,
        user_id=user.id,
        payment_id=payment.id,
        days=30
    )
    
    text = """
🎉 <b>Поздравляем! Премиум активирован!</b>

Ваша премиум подписка успешно активирована на 30 дней.

<b>Теперь вам доступно:</b>
📋 До 10 списков задач
🔔 Кастомные уведомления для каждой задачи
⚡ Приоритетная поддержка

Спасибо за поддержку! 💙

Приятного использования! ✨
"""
    
    is_admin = message.from_user.id in config.ADMIN_IDS
    await message.answer(
        text=text,
        reply_markup=main_menu_keyboard(is_premium=True, is_admin=is_admin)
    )


@router.callback_query(F.data == "set_daily_summary")
async def set_daily_summary_start(callback: CallbackQuery, user: User, state: FSMContext):
    """Начать настройку ежедневной сводки"""
    if not user.is_premium:
        await callback.answer("⭐ Эта функция доступна только для премиум пользователей", show_alert=True)
        return
    
    current_time = user.daily_summary_time or "не установлено"
    
    text = f"""
📊 <b>Настройка ежедневной сводки</b>

<b>Текущее время:</b> {current_time}

Ежедневная сводка — это уведомление со всеми вашими активными списками и задачами.

Введите время в формате <b>HH:MM</b>, когда вы хотите получать сводку.

Например: <b>09:00</b> или <b>20:00</b>

Чтобы отключить сводку, введите: <b>off</b>
"""
    
    await callback.message.edit_text(
        text=text,
        reply_markup=cancel_keyboard()
    )
    await state.set_state(SetDailySummaryStates.waiting_for_time)
    await callback.answer()


@router.message(SetDailySummaryStates.waiting_for_time)
async def set_daily_summary_finish(message: Message, session: AsyncSession, user: User, state: FSMContext):
    """Завершить настройку ежедневной сводки"""
    time_text = message.text.strip().lower()
    
    # Проверка на отключение
    if time_text == "off":
        await UserCRUD.update_daily_summary_time(session, user.id, None)
        
        text = """
✅ <b>Ежедневная сводка отключена</b>

Вы больше не будете получать ежедневные сводки.
Вы можете снова включить их в любое время через Профиль.
"""
        
        await message.answer(
            text=text,
            reply_markup=back_to_profile_keyboard()
        )
        await state.clear()
        return
    
    # Валидация формата времени
    try:
        hours, minutes = time_text.split(":")
        hours = int(hours)
        minutes = int(minutes)
        
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError
        
        time_formatted = f"{hours:02d}:{minutes:02d}"
    except:
        await message.answer("❌ Неверный формат времени. Используйте формат HH:MM (например, 09:00) или введите 'off' для отключения")
        return
    
    # Сохраняем время
    await UserCRUD.update_daily_summary_time(session, user.id, time_formatted)
    
    text = f"""
✅ <b>Ежедневная сводка настроена!</b>

Вы будете получать сводку со всеми активными задачами каждый день в {time_formatted}

Сводка включает:
📋 Все ваши активные списки
📝 Все активные задачи из всех списков
📊 Общую статистику

Вы можете изменить время или отключить сводку в любое время через Профиль.
"""
    
    await message.answer(
        text=text,
        reply_markup=back_to_profile_keyboard()
    )
    await state.clear()
