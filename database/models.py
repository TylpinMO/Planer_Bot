"""Модели базы данных"""
from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from config import config


class Base(AsyncAttrs, DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    premium_notified_3days: Mapped[bool] = mapped_column(Boolean, default=False)  # Уведомление за 3 дня
    premium_notified_2days: Mapped[bool] = mapped_column(Boolean, default=False)  # Уведомление за 2 дня
    premium_notified_1day: Mapped[bool] = mapped_column(Boolean, default=False)   # Уведомление за 1 день
    timezone_offset: Mapped[int] = mapped_column(Integer, default=3)  # Смещение в часах от UTC (по умолчанию +3 МСК)
    daily_summary_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # Время ежедневной сводки для премиум (HH:MM)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    task_lists: Mapped[list["TaskList"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User {self.telegram_id} ({self.username})>"


class TaskList(Base):
    """Модель списка задач"""
    __tablename__ = "task_lists"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    notification_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # Формат "HH:MM"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    user: Mapped["User"] = relationship(back_populates="task_lists")
    tasks: Mapped[list["Task"]] = relationship(back_populates="task_list", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<TaskList {self.id}: {self.name}>"


class Task(Base):
    """Модель задачи"""
    __tablename__ = "tasks"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("task_lists.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notification_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # Только для премиум
    priority: Mapped[int] = mapped_column(Integer, default=0)  # 0-низкий, 1-средний, 2-высокий
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Связи
    task_list: Mapped["TaskList"] = relationship(back_populates="tasks")
    
    def __repr__(self) -> str:
        return f"<Task {self.id}: {self.text[:30]}...>"


class Subscription(Base):
    """Модель подписки"""
    __tablename__ = "subscriptions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    payment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("payments.id"), nullable=True)
    
    # Связи
    user: Mapped["User"] = relationship(back_populates="subscriptions")
    payment: Mapped[Optional["Payment"]] = relationship(back_populates="subscription")
    
    def __repr__(self) -> str:
        return f"<Subscription {self.id} for User {self.user_id}>"


class Payment(Base):
    """Модель платежа (для статистики)"""
    __tablename__ = "payments"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    telegram_payment_charge_id: Mapped[str] = mapped_column(String(255), unique=True)
    amount_stars: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(50), default="completed")  # pending, completed, refunded
    
    # Связи
    user: Mapped["User"] = relationship(back_populates="payments")
    subscription: Mapped[Optional["Subscription"]] = relationship(back_populates="payment")
    
    def __repr__(self) -> str:
        return f"<Payment {self.id}: {self.amount_stars} stars>"


# Создание движка и сессии
engine = create_async_engine(config.DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    """Получение сессии базы данных"""
    async with async_session_maker() as session:
        yield session
