"""Middleware для проверки доступа и лимитов"""
from typing import Callable, Dict, Any, Awaitable, Union
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import async_session_maker
from database.crud import UserCRUD


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для добавления сессии БД"""
    
    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        async with async_session_maker() as session:
            data["session"] = session
            return await handler(event, data)


class UserMiddleware(BaseMiddleware):
    """Middleware для автоматической регистрации пользователей"""
    
    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        session: AsyncSession = data.get("session")
        
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        else:
            return await handler(event, data)
        
        # Получаем или создаем пользователя
        db_user = await UserCRUD.get_or_create(
            session=session,
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        
        data["user"] = db_user
        return await handler(event, data)
