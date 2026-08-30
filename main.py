"""Точка входа приложения"""
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from config import config
from database.models import init_db
from bot.handlers import register_handlers
from services.notifications import NotificationService


# Создаем директорию для логов
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Настройка логирования с ротацией файлов
file_handler = RotatingFileHandler(
    logs_dir / "bot.log",
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5,  # Хранить 5 файлов
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)

# Консольный handler для критичных ошибок
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
)

# Настройка root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

# Для нашего бота
logger = logging.getLogger(__name__)

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
    bot = Bot(
        token=config.BOT_TOKEN,
        parse_mode=ParseMode.HTML
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
