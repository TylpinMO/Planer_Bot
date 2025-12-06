"""Сервис уведомлений"""
import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from database.models import async_session_maker, User, TaskList, Task
from bot.keyboards.inline import main_menu_keyboard, premium_renew_keyboard
from config import config

logger = logging.getLogger(__name__)

# Московский часовой пояс (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))


class NotificationService:
    """Сервис для отправки уведомлений"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)
    
    def start(self):
        """Запустить планировщик"""
        logger.info("Запуск сервиса уведомлений...")
        
        # Добавляем задачу проверки уведомлений каждую минуту
        self.scheduler.add_job(
            self.check_notifications,
            'cron',
            minute='*',
            id='check_notifications',
            timezone=MOSCOW_TZ
        )
        
        self.scheduler.start()
        logger.info("Сервис уведомлений запущен (часовой пояс: UTC+3 Москва)")
    
    def stop(self):
        """Остановить планировщик"""
        logger.info("Остановка сервиса уведомлений...")
        self.scheduler.shutdown()
        logger.info("Сервис уведомлений остановлен")
    
    async def check_notifications(self):
        """Проверка и отправка уведомлений"""
        moscow_time = datetime.now(MOSCOW_TZ)
        
        async with async_session_maker() as session:
            # Проверяем истечение премиума раз в день в 10:00 по МСК
            if moscow_time.hour == 10 and moscow_time.minute == 0:
                await self._check_premium_expiration(session)
            
            # Проходим по всем возможным часовым поясам (-12 до +14)
            for tz_offset in range(-12, 15):
                tz = timezone(timedelta(hours=tz_offset))
                current_time = datetime.now(tz).strftime('%H:%M')
                
                # Уведомления для списков в этом часовом поясе
                await self._check_list_notifications(session, current_time, tz_offset)
                
                # Уведомления для задач в этом часовом поясе (только премиум)
                await self._check_task_notifications(session, current_time, tz_offset)
                
                # Ежедневная сводка для премиум пользователей
                await self._check_daily_summary(session, current_time, tz_offset)
    
    async def _check_list_notifications(self, session, current_time: str, tz_offset: int):
        """Проверка уведомлений для списков"""
        # Находим списки с уведомлениями на текущее время для пользователей с этим часовым поясом
        result = await session.execute(
            select(TaskList)
            .join(TaskList.user)
            .where(
                and_(
                    TaskList.notification_time == current_time,
                    TaskList.is_active == True,
                    User.timezone_offset == tz_offset
                )
            )
            .options(selectinload(TaskList.tasks), selectinload(TaskList.user))
        )
        
        task_lists = result.scalars().all()
        
        for task_list in task_lists:
            await self._send_list_notification(task_list)
    
    async def _check_task_notifications(self, session, current_time: str, tz_offset: int):
        """Проверка уведомлений для задач (премиум)"""
        # Находим задачи с уведомлениями на текущее время для пользователей с этим часовым поясом
        result = await session.execute(
            select(Task)
            .join(Task.task_list)
            .join(TaskList.user)
            .where(
                and_(
                    Task.notification_time == current_time,
                    Task.is_completed == False,
                    User.is_premium == True,
                    User.timezone_offset == tz_offset
                )
            )
            .options(
                selectinload(Task.task_list).selectinload(TaskList.user)
            )
        )
        
        tasks = result.scalars().all()
        
        for task in tasks:
            await self._send_task_notification(task)
    
    async def _send_list_notification(self, task_list: TaskList):
        """Отправить уведомление о списке"""
        try:
            # Получаем активные задачи
            active_tasks = [t for t in task_list.tasks if not t.is_completed]
            
            if not active_tasks:
                logger.debug(f"Список {task_list.id} не имеет активных задач, пропускаем уведомление")
                return
            
            # Формируем текст уведомления
            text = f"""
🔔 <b>Уведомление: {task_list.name}</b>

<b>Активных задач: {len(active_tasks)}</b>

"""
            
            for i, task in enumerate(active_tasks[:10], 1):
                priority_emoji = {0: "", 1: "🔸", 2: "🔴"}
                text += f"{i}. {priority_emoji.get(task.priority, '')} {task.text[:50]}"
                if len(task.text) > 50:
                    text += "..."
                text += "\n"
            
            if len(active_tasks) > 10:
                text += f"\n<i>... и ещё {len(active_tasks) - 10} задач</i>"
            
            text += "\n\n💪 Продуктивного дня!"
            
            # Отправляем уведомление с кнопкой
            is_admin = task_list.user.telegram_id in config.ADMIN_IDS
            await self.bot.send_message(
                chat_id=task_list.user.telegram_id,
                text=text,
                reply_markup=main_menu_keyboard(task_list.user.is_premium, is_admin)
            )
        
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о списке {task_list.id}: {e}")
    
    async def _send_task_notification(self, task: Task):
        """Отправить уведомление о задаче"""
        try:
            priority_text = {0: "", 1: "🔸 Средний приоритет", 2: "🔴 Высокий приоритет"}
            priority_info = priority_text.get(task.priority, "")
            
            text = f"""
🔔 <b>Напоминание о задаче</b>

{task.text}

"""
            
            if priority_info:
                text += f"{priority_info}\n"
            
            if task.deadline:
                text += f"⏰ Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}\n"
            
            text += f"\n\n📋 Список: {task.task_list.name}"
            text += "\n\n✅ Не забудьте отметить выполненной!"
            
            # Отправляем уведомление с кнопкой
            is_admin = task.task_list.user.telegram_id in config.ADMIN_IDS
            await self.bot.send_message(
                chat_id=task.task_list.user.telegram_id,
                text=text,
                reply_markup=main_menu_keyboard(task.task_list.user.is_premium, is_admin)
            )
        
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о задаче {task.id}: {e}")
    
    async def _check_daily_summary(self, session, current_time: str, tz_offset: int):
        """Проверка и отправка ежедневной сводки для премиум пользователей"""
        # Находим премиум пользователей с установленным временем сводки
        result = await session.execute(
            select(User)
            .where(
                and_(
                    User.is_premium == True,
                    User.daily_summary_time == current_time,
                    User.timezone_offset == tz_offset
                )
            )
            .options(
                selectinload(User.task_lists).selectinload(TaskList.tasks)
            )
        )
        
        users = result.scalars().all()
        
        for user in users:
            await self._send_daily_summary(user)
    
    async def _send_daily_summary(self, user: User):
        """Отправить ежедневную сводку со всеми списками и задачами"""
        try:
            # Получаем все активные списки
            active_lists = [lst for lst in user.task_lists if lst.is_active]
            
            if not active_lists:
                logger.debug(f"У пользователя {user.telegram_id} нет активных списков")
                return
            
            # Собираем все активные задачи
            total_tasks = 0
            text = "📊 <b>Ежедневная сводка по всем задачам</b>\n\n"
            
            for task_list in active_lists:
                active_tasks = [t for t in task_list.tasks if not t.is_completed]
                total_tasks += len(active_tasks)
                
                if active_tasks:
                    text += f"📋 <b>{task_list.name}</b> ({len(active_tasks)})\n"
                    
                    for i, task in enumerate(active_tasks[:5], 1):
                        priority_emoji = {0: "", 1: "🔸", 2: "🔴"}
                        text += f"  {i}. {priority_emoji.get(task.priority, '')} {task.text[:40]}"
                        if len(task.text) > 40:
                            text += "..."
                        text += "\n"
                    
                    if len(active_tasks) > 5:
                        text += f"  <i>... и ещё {len(active_tasks) - 5}</i>\n"
                    
                    text += "\n"
            
            if total_tasks == 0:
                text += "<i>Все задачи выполнены! 🎉</i>\n"
            else:
                text += f"<b>Всего активных задач: {total_tasks}</b>\n"
            
            text += "\n💪 Продуктивного дня!"
            
            # Отправляем сводку
            is_admin = user.telegram_id in config.ADMIN_IDS
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                reply_markup=main_menu_keyboard(user.is_premium, is_admin)
            )
        
        except Exception as e:
            logger.error(f"Ошибка при отправке ежедневной сводки пользователю {user.telegram_id}: {e}")
    
    async def _check_premium_expiration(self, session):
        """Проверка истечения премиума и отправка уведомлений"""
        now = datetime.utcnow()
        
        # Обрабатываем истёкший премиум
        await self._handle_expired_premium(session, now)
        
        # За 3 дня
        three_days_later = now + timedelta(days=3)
        result = await session.execute(
            select(User).where(
                and_(
                    User.is_premium == True,
                    User.premium_until != None,
                    User.premium_until <= three_days_later,
                    User.premium_until > now + timedelta(days=2),
                    User.premium_notified_3days == False
                )
            )
        )
        users_3days = result.scalars().all()
        
        for user in users_3days:
            await self._send_premium_expiration_notice(user, 3)
            user.premium_notified_3days = True
        
        # За 2 дня
        two_days_later = now + timedelta(days=2)
        result = await session.execute(
            select(User).where(
                and_(
                    User.is_premium == True,
                    User.premium_until != None,
                    User.premium_until <= two_days_later,
                    User.premium_until > now + timedelta(days=1),
                    User.premium_notified_2days == False
                )
            )
        )
        users_2days = result.scalars().all()
        
        for user in users_2days:
            await self._send_premium_expiration_notice(user, 2)
            user.premium_notified_2days = True
        
        # За 1 день
        one_day_later = now + timedelta(days=1)
        result = await session.execute(
            select(User).where(
                and_(
                    User.is_premium == True,
                    User.premium_until != None,
                    User.premium_until <= one_day_later,
                    User.premium_until > now,
                    User.premium_notified_1day == False
                )
            )
        )
        users_1day = result.scalars().all()
        
        for user in users_1day:
            await self._send_premium_expiration_notice(user, 1)
            user.premium_notified_1day = True
        
        await session.commit()
    
    async def _send_premium_expiration_notice(self, user: User, days: int):
        """Отправить уведомление об истечении премиума"""
        try:
            days_text = {
                3: "3 дня",
                2: "2 дня", 
                1: "1 день"
            }
            
            text = f"""
⚠️ <b>Окончание премиум-подписки</b>

Ваша премиум-подписка закончится через {days_text.get(days, f'{days} дней')}.

<b>Дата окончания:</b> {user.premium_until.strftime('%d.%m.%Y')}

После окончания:
• Останется только 1 список задач
• Кастомные уведомления задач будут отключены
• Остальные списки будут скрыты (но не удалены)

💡 Продлите подписку, чтобы сохранить все возможности!
"""
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                reply_markup=premium_renew_keyboard()
            )
            
            logger.info(f"Отправлено уведомление об истечении премиума пользователю {user.telegram_id} (за {days} дней)")
        
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об истечении премиума {user.telegram_id}: {e}")
    
    async def _handle_expired_premium(self, session, now: datetime):
        """Обработка истёкшего премиума"""
        # Находим пользователей с истёкшим премиумом
        result = await session.execute(
            select(User).where(
                and_(
                    User.is_premium == True,
                    User.premium_until != None,
                    User.premium_until <= now
                )
            )
        )
        expired_users = result.scalars().all()
        
        for user in expired_users:
            logger.info(f"Обработка истёкшего премиума для пользователя {user.telegram_id}")
            
            # Отключаем премиум
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
                        logger.info(f"Список {task_list.id} ({task_list.name}) скрыт")
            
            # Отключаем кастомные уведомления задач
            for task_list in lists:
                tasks = await TaskCRUD.get_list_tasks(session, task_list.id, include_completed=False)
                for task in tasks:
                    if task.notification_time:
                        task.notification_time = None
                        logger.info(f"Кастомное уведомление задачи {task.id} отключено")
            
            # Отправляем уведомление об окончании премиума
            try:
                hidden_count = len(lists) - 1 if len(lists) > 1 else 0
                text = f"""
😔 <b>Премиум-подписка закончилась</b>

Ваша премиум-подписка истекла.

<b>Что изменилось:</b>
• Доступен только 1 список задач
• Кастомные уведомления задач отключены
{'• ' + str(hidden_count) + ' списков скрыто (но не удалено)' if hidden_count > 0 else ''}

💡 Ваши данные сохранены! При продлении подписки все списки и задачи станут снова доступны.

⭐ Хотите вернуть все функции? Оформите премиум!
"""
                
                await self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=text,
                    reply_markup=premium_renew_keyboard()
                )
                
                logger.info(f"Отправлено уведомление об окончании премиума пользователю {user.telegram_id}")
            
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления об окончании премиума {user.telegram_id}: {e}")
        
        if expired_users:
            await session.commit()

