"""CRUD операции для работы с базой данных"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import User, TaskList, Task, Subscription, Payment


class UserCRUD:
    """CRUD операции для пользователей"""
    
    @staticmethod
    async def get_or_create(session: AsyncSession, telegram_id: int, username: str = None, first_name: str = None) -> User:
        """Получить или создать пользователя"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        
        return user
    
    @staticmethod
    async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
        """Получить пользователя по telegram_id"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def set_premium(session: AsyncSession, user_id: int, days: int = 30) -> User:
        """Установить премиум статус или продлить существующий"""
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one()
        
        user.is_premium = True
        
        # Если у пользователя уже есть активный премиум, добавляем дни к текущей дате окончания
        if user.premium_until and user.premium_until > datetime.utcnow():
            user.premium_until = user.premium_until + timedelta(days=days)
        else:
            # Если премиума нет или он истёк, устанавливаем новую дату
            user.premium_until = datetime.utcnow() + timedelta(days=days)
        
        # Сбрасываем флаги уведомлений при продлении
        user.premium_notified_3days = False
        user.premium_notified_2days = False
        user.premium_notified_1day = False
        
        await session.commit()
        await session.refresh(user)
        return user
    
    @staticmethod
    async def remove_premium(session: AsyncSession, user_id: int) -> User:
        """Удалить премиум статус"""
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one()
        
        user.is_premium = False
        user.premium_until = None
        
        await session.commit()
        await session.refresh(user)
        return user
    
    @staticmethod
    async def update_timezone(session: AsyncSession, user_id: int, timezone_offset: int) -> User:
        """Обновить часовой пояс пользователя"""
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one()
        
        user.timezone_offset = timezone_offset
        
        await session.commit()
        await session.refresh(user)
        return user
    
    @staticmethod
    async def update_daily_summary_time(session: AsyncSession, user_id: int, daily_summary_time: str = None) -> User:
        """Обновить время ежедневной сводки для премиум пользователя"""
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one()
        
        user.daily_summary_time = daily_summary_time
        
        await session.commit()
        await session.refresh(user)
        return user
    
    @staticmethod
    async def get_all_users(session: AsyncSession) -> List[User]:
        """Получить всех пользователей"""
        result = await session.execute(select(User))
        return list(result.scalars().all())
    
    @staticmethod
    async def get_premium_users(session: AsyncSession) -> List[User]:
        """Получить всех премиум пользователей"""
        result = await session.execute(
            select(User).where(User.is_premium == True)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_stats(session: AsyncSession) -> dict:
        """Получить статистику пользователей"""
        total_result = await session.execute(select(func.count(User.id)))
        total_count = total_result.scalar()
        
        premium_result = await session.execute(
            select(func.count(User.id)).where(User.is_premium == True)
        )
        premium_count = premium_result.scalar()
        
        return {
            "total": total_count,
            "premium": premium_count,
            "free": total_count - premium_count
        }


class TaskListCRUD:
    """CRUD операции для списков задач"""
    
    @staticmethod
    async def create(session: AsyncSession, user_id: int, name: str, notification_time: str = None) -> TaskList:
        """Создать список задач"""
        task_list = TaskList(
            user_id=user_id,
            name=name,
            notification_time=notification_time
        )
        session.add(task_list)
        await session.commit()
        await session.refresh(task_list)
        return task_list
    
    @staticmethod
    async def get_user_lists(session: AsyncSession, user_id: int) -> List[TaskList]:
        """Получить все списки пользователя"""
        result = await session.execute(
            select(TaskList)
            .where(TaskList.user_id == user_id, TaskList.is_active == True)
            .options(selectinload(TaskList.tasks))
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_id(session: AsyncSession, list_id: int) -> Optional[TaskList]:
        """Получить список по ID"""
        result = await session.execute(
            select(TaskList)
            .where(TaskList.id == list_id)
            .options(selectinload(TaskList.tasks))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_notification_time(session: AsyncSession, list_id: int, notification_time: str) -> TaskList:
        """Обновить время уведомлений"""
        result = await session.execute(
            select(TaskList).where(TaskList.id == list_id)
        )
        task_list = result.scalar_one()
        task_list.notification_time = notification_time
        
        await session.commit()
        await session.refresh(task_list)
        return task_list
    
    @staticmethod
    async def delete(session: AsyncSession, list_id: int):
        """Удалить список (мягкое удаление)"""
        result = await session.execute(
            select(TaskList).where(TaskList.id == list_id)
        )
        task_list = result.scalar_one()
        task_list.is_active = False
        
        await session.commit()
    
    @staticmethod
    async def count_user_lists(session: AsyncSession, user_id: int) -> int:
        """Подсчитать количество списков пользователя"""
        result = await session.execute(
            select(func.count(TaskList.id)).where(
                and_(TaskList.user_id == user_id, TaskList.is_active == True)
            )
        )
        return result.scalar()


class TaskCRUD:
    """CRUD операции для задач"""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        list_id: int,
        text: str,
        deadline: datetime = None,
        notification_time: str = None,
        priority: int = 0
    ) -> Task:
        """Создать задачу"""
        task = Task(
            list_id=list_id,
            text=text,
            deadline=deadline,
            notification_time=notification_time,
            priority=priority
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task
    
    @staticmethod
    async def get_by_id(session: AsyncSession, task_id: int) -> Optional[Task]:
        """Получить задачу по ID"""
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_list_tasks(session: AsyncSession, list_id: int, include_completed: bool = True) -> List[Task]:
        """Получить все задачи списка"""
        query = select(Task).where(Task.list_id == list_id)
        
        if not include_completed:
            query = query.where(Task.is_completed == False)
        
        result = await session.execute(query.order_by(Task.priority.desc(), Task.created_at))
        return list(result.scalars().all())
    
    @staticmethod
    async def toggle_complete(session: AsyncSession, task_id: int) -> Task:
        """Переключить статус выполнения задачи"""
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one()
        
        task.is_completed = not task.is_completed
        task.completed_at = datetime.utcnow() if task.is_completed else None
        
        await session.commit()
        await session.refresh(task)
        return task
    
    @staticmethod
    async def update_notification(session: AsyncSession, task_id: int, notification_time: str) -> Task:
        """Обновить время уведомления задачи"""
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one()
        task.notification_time = notification_time
        
        await session.commit()
        await session.refresh(task)
        
        return task
    
    @staticmethod
    async def delete(session: AsyncSession, task_id: int):
        """Удалить задачу"""
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one()
        await session.delete(task)
        await session.commit()


class SubscriptionCRUD:
    """CRUD операции для подписок"""
    
    @staticmethod
    async def create(session: AsyncSession, user_id: int, payment_id: int = None, days: int = 30) -> Subscription:
        """Создать подписку"""
        subscription = Subscription(
            user_id=user_id,
            payment_id=payment_id,
            expires_at=datetime.utcnow() + timedelta(days=days)
        )
        session.add(subscription)
        await session.commit()
        await session.refresh(subscription)
        return subscription
    
    @staticmethod
    async def get_user_subscriptions(session: AsyncSession, user_id: int) -> List[Subscription]:
        """Получить все подписки пользователя"""
        result = await session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_active_subscription(session: AsyncSession, user_id: int) -> Optional[Subscription]:
        """Получить активную подписку пользователя"""
        result = await session.execute(
            select(Subscription).where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.is_active == True,
                    Subscription.expires_at > datetime.utcnow()
                )
            )
            .order_by(Subscription.expires_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class PaymentCRUD:
    """CRUD операции для платежей"""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        user_id: int,
        telegram_payment_charge_id: str,
        amount_stars: int
    ) -> Payment:
        """Создать запись о платеже"""
        payment = Payment(
            user_id=user_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
            amount_stars=amount_stars
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment
    
    @staticmethod
    async def get_all_payments(session: AsyncSession) -> List[Payment]:
        """Получить все платежи"""
        result = await session.execute(
            select(Payment).order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_stats(session: AsyncSession) -> dict:
        """Получить статистику платежей"""
        total_count = await session.execute(select(func.count(Payment.id)))
        total_stars = await session.execute(select(func.sum(Payment.amount_stars)))
        
        return {
            "total_payments": total_count.scalar() or 0,
            "total_stars": total_stars.scalar() or 0
        }
