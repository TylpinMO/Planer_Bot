"""Конфигурация проекта"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Основные настройки приложения"""
    
    # Telegram Bot
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./planner.db")
    
    # Premium Settings
    PREMIUM_PRICE_STARS = int(os.getenv("PREMIUM_PRICE_STARS", "250"))
    
    # Limits
    FREE_LISTS_LIMIT = 1
    PREMIUM_LISTS_LIMIT = 10
    FREE_NOTIFICATIONS_PER_LIST = 1
    
    @classmethod
    def validate(cls):
        """Проверка обязательных параметров"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в .env файле")
        if not cls.ADMIN_IDS:
            raise ValueError("ADMIN_IDS не установлен в .env файле")


config = Config()
