"""Миграция существующей базы данных к актуальной версии"""
import asyncio
import logging
from sqlalchemy import text
from database.models import async_session_maker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    """Применить все необходимые миграции"""
    async with async_session_maker() as session:
        migrations_applied = []
        
        try:
            # Миграция 1: Добавление timezone_offset
            try:
                await session.execute(
                    text("ALTER TABLE users ADD COLUMN timezone_offset INTEGER DEFAULT 3")
                )
                migrations_applied.append("timezone_offset")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    logger.debug("timezone_offset уже существует")
                else:
                    raise
            
            # Миграция 2: Добавление полей уведомлений о премиуме
            try:
                await session.execute(
                    text("ALTER TABLE users ADD COLUMN premium_notified_3days BOOLEAN DEFAULT 0")
                )
                migrations_applied.append("premium_notified_3days")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    logger.debug("premium_notified_3days уже существует")
                else:
                    raise
            
            try:
                await session.execute(
                    text("ALTER TABLE users ADD COLUMN premium_notified_2days BOOLEAN DEFAULT 0")
                )
                migrations_applied.append("premium_notified_2days")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    logger.debug("premium_notified_2days уже существует")
                else:
                    raise
            
            try:
                await session.execute(
                    text("ALTER TABLE users ADD COLUMN premium_notified_1day BOOLEAN DEFAULT 0")
                )
                migrations_applied.append("premium_notified_1day")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    logger.debug("premium_notified_1day уже существует")
                else:
                    raise
            
            # Миграция 3: Добавление daily_summary_time
            try:
                await session.execute(
                    text("ALTER TABLE users ADD COLUMN daily_summary_time VARCHAR(5)")
                )
                migrations_applied.append("daily_summary_time")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    logger.debug("daily_summary_time уже существует")
                else:
                    raise
            
            await session.commit()
            
            if migrations_applied:
                logger.info(f"✅ Применены миграции: {', '.join(migrations_applied)}")
            else:
                logger.info("ℹ️  База данных уже актуальна, миграции не требуются")
                
        except Exception as e:
            logger.error(f"❌ Ошибка миграции: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(migrate())
