"""Сервис для работы с платежами Telegram Stars"""
import logging
from aiogram.types import LabeledPrice
from config import config

logger = logging.getLogger(__name__)


class PaymentService:
    """Сервис для обработки платежей"""
    
    PREMIUM_TITLE = "Премиум подписка"
    PREMIUM_DESCRIPTION = """
⭐ Премиум подписка на 30 дней

Что входит:
• 10 списков задач (вместо 1)
• Кастомные уведомления для каждой задачи
• Приоритетная поддержка

Цена: 250 звёзд
"""
    
    @staticmethod
    def get_premium_invoice_data() -> dict:
        """Получить данные для создания инвойса премиум подписки"""
        return {
            "title": PaymentService.PREMIUM_TITLE,
            "description": PaymentService.PREMIUM_DESCRIPTION,
            "payload": "premium_subscription_30days",
            "currency": "XTR",  # Telegram Stars
            "prices": [
                LabeledPrice(
                    label="Премиум подписка (30 дней)",
                    amount=config.PREMIUM_PRICE_STARS
                )
            ]
        }
    
    @staticmethod
    def validate_payment(payload: str, amount: int) -> bool:
        """Валидация платежа"""
        if payload != "premium_subscription_30days":
            logger.warning(f"Неверный payload платежа: {payload}")
            return False
        
        if amount != config.PREMIUM_PRICE_STARS:
            logger.warning(f"Неверная сумма платежа: {amount}, ожидалось {config.PREMIUM_PRICE_STARS}")
            return False
        
        return True
