"""Точка входа приложения"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from config import config
from database.models import init_db
from bot.handlers import register_handlers
from services.notifications import NotificationService


# Настройка минимального логирования
logging.basicConfig(
    level=logging.WARNING,  # Только WARNING и ERROR
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Для нашего бота оставляем только критичные сообщения
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Отключаем подробное логирование библиотек
logging.getLogger('aiogram').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)


async def main():
    """Главная функция запуска бота"""
    
    # Валидация конфигурации
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        return
    
    # Инициализация базы данных
    logger.info("Инициализация базы данных...")
    await init_db()
    
    # Инициализация бота и диспетчера
    from aiogram.client.default import DefaultBotProperties
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Регистрация обработчиков
    register_handlers(dp)
    
    # Запуск сервиса уведомлений
    notification_service = NotificationService(bot)
    notification_service.start()
    
    logger.info("Бот запущен!")
    
    try:
        # Удаление вебхуков и запуск polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        notification_service.stop()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
