"""Middleware для проверки статуса премиум подписки"""
import logging
from typing import Callable, Dict, Any, Awaitable, Union
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from bot.utils.datetime_helpers import utc_now

logger = logging.getLogger(__name__)


class PremiumCheckMiddleware(BaseMiddleware):
    """
    Middleware для автоматической проверки истечения премиум подписки.
    Проверяет при каждом запросе пользователя и автоматически отключает
    истёкший премиум.
    """
    
    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get("user")
        session: AsyncSession = data.get("session")
        
        if user and session:
            # Проверяем, истёк ли премиум
            if user.is_premium and user.premium_until:
                current_time = utc_now()
                
                if user.premium_until <= current_time:
                    # Премиум истёк - отключаем
                    logger.info(f"Автоматическое отключение истёкшего премиума для пользователя {user.telegram_id}")
                    
                    user.is_premium = False
                    
                    # Скрываем лишние списки (оставляем только 1)
                    from database.crud import TaskListCRUD, TaskCRUD
                    lists = await TaskListCRUD.get_user_lists(session, user.id)
                    
                    if len(lists) > 1:
                        # Оставляем активным только первый список
                        for i, task_list in enumerate(lists):
                            if i == 0:
                                task_list.is_active = True
                            else:
                                task_list.is_active = False
                    
                    # Отключаем кастомные уведомления задач
                    for task_list in lists:
                        tasks = await TaskCRUD.get_list_tasks(session, task_list.id, include_completed=False)
                        for task in tasks:
                            if task.notification_time:
                                task.notification_time = None
                    
                    await session.commit()
                    logger.info(f"Премиум отключён для пользователя {user.telegram_id}")
        
        # Продолжаем обработку запроса
        return await handler(event, data)
