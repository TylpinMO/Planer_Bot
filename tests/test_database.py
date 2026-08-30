import unittest
from datetime import timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.utils.datetime_helpers import utc_now_naive
from database.crud import TaskCRUD, TaskListCRUD, UserCRUD
from database.models import Base


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.session = async_sessionmaker(self.engine, expire_on_commit=False)()
        self.user = await UserCRUD.get_or_create(self.session, 101, "test_user", "Тест")
        self.task_list = await TaskListCRUD.create(self.session, self.user.id, "Работа")

    async def asyncTearDown(self):
        await self.session.close()
        await self.engine.dispose()

    async def test_user_registration_is_idempotent(self):
        same_user = await UserCRUD.get_or_create(self.session, 101)
        self.assertEqual(same_user.id, self.user.id)
        self.assertEqual((await UserCRUD.get_stats(self.session))["total"], 1)

    async def test_users_have_separate_lists(self):
        other = await UserCRUD.get_or_create(self.session, 202)
        await TaskListCRUD.create(self.session, other.id, "Личное")
        lists = await TaskListCRUD.get_user_lists(self.session, self.user.id)
        self.assertEqual([item.id for item in lists], [self.task_list.id])

    async def test_task_completion_can_be_reversed(self):
        task = await TaskCRUD.create(self.session, self.task_list.id, "Проверить сборку")
        completed = await TaskCRUD.toggle_complete(self.session, task.id)
        self.assertTrue(completed.is_completed)
        self.assertIsNotNone(completed.completed_at)
        self.assertEqual(await TaskCRUD.get_list_tasks(self.session, self.task_list.id, False), [])
        restored = await TaskCRUD.toggle_complete(self.session, task.id)
        self.assertFalse(restored.is_completed)
        self.assertIsNone(restored.completed_at)

    async def test_tasks_are_sorted_by_priority(self):
        low = await TaskCRUD.create(self.session, self.task_list.id, "Позже", priority=0)
        high = await TaskCRUD.create(self.session, self.task_list.id, "Сейчас", priority=2)
        tasks = await TaskCRUD.get_list_tasks(self.session, self.task_list.id)
        self.assertEqual([task.id for task in tasks], [high.id, low.id])

    async def test_deleted_list_is_not_counted(self):
        await TaskListCRUD.delete(self.session, self.task_list.id)
        self.assertEqual(await TaskListCRUD.count_user_lists(self.session, self.user.id), 0)
        self.assertEqual(await TaskListCRUD.get_user_lists(self.session, self.user.id), [])

    async def test_premium_renewal_preserves_remaining_days(self):
        self.user.premium_until = utc_now_naive() + timedelta(days=10)
        previous_end = self.user.premium_until
        await self.session.commit()
        renewed = await UserCRUD.set_premium(self.session, self.user.id, days=30)
        self.assertEqual(renewed.premium_until, previous_end + timedelta(days=30))
        self.assertTrue(renewed.is_premium)

    async def test_premium_removal_clears_expiry(self):
        await UserCRUD.set_premium(self.session, self.user.id)
        removed = await UserCRUD.remove_premium(self.session, self.user.id)
        self.assertFalse(removed.is_premium)
        self.assertIsNone(removed.premium_until)
