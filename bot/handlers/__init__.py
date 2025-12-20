"""Пакет обработчиков команд"""
from aiogram import Dispatcher

from bot.handlers import basic, lists, tasks, premium, admin
from bot.middlewares.user import DatabaseMiddleware, UserMiddleware
from bot.middlewares.premium import PremiumCheckMiddleware


def register_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков"""
    # Регистрация middleware
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())
    
    # Middleware для проверки истечения премиума
    dp.message.middleware(PremiumCheckMiddleware())
    dp.callback_query.middleware(PremiumCheckMiddleware())
    
    # Регистрация роутеров
    dp.include_router(admin.router)  # Админ команды первыми
    dp.include_router(basic.router)
    dp.include_router(lists.router)
    dp.include_router(tasks.router)
    dp.include_router(premium.router)
