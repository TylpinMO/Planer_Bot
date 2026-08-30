import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bot.handlers import lists, tasks


class AccessTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=10, is_premium=True)
        self.session = object()
        self.state = AsyncMock()
        self.task = SimpleNamespace(id=5, list_id=7)
        self.foreign_list = SimpleNamespace(id=7, user_id=99, is_active=True)
        self.callback = SimpleNamespace(
            data="toggle_task_5", answer=AsyncMock(),
            message=SimpleNamespace(edit_text=AsyncMock()),
        )

    async def test_cannot_toggle_another_users_task(self):
        with patch.object(tasks.TaskCRUD, "get_by_id", AsyncMock(return_value=self.task)), \
             patch.object(tasks.TaskListCRUD, "get_by_id", AsyncMock(return_value=self.foreign_list)), \
             patch.object(tasks.TaskCRUD, "toggle_complete", AsyncMock()) as mutate:
            await tasks.toggle_task_status(self.callback, self.session, self.user)
            mutate.assert_not_awaited()
            self.callback.answer.assert_awaited_once()

    async def test_missing_task_is_not_mutated(self):
        with patch.object(tasks.TaskCRUD, "get_by_id", AsyncMock(return_value=None)), \
             patch.object(tasks.TaskCRUD, "toggle_complete", AsyncMock()) as mutate:
            await tasks.toggle_task_status(self.callback, self.session, self.user)
            mutate.assert_not_awaited()

    async def test_cannot_configure_another_users_task(self):
        self.callback.data = "task_notify_5"
        with patch.object(tasks.TaskCRUD, "get_by_id", AsyncMock(return_value=self.task)), \
             patch.object(tasks.TaskListCRUD, "get_by_id", AsyncMock(return_value=self.foreign_list)):
            await tasks.set_task_notification_start(self.callback, self.user, self.state, self.session)
            self.state.set_state.assert_not_awaited()

    async def test_cannot_configure_another_users_list(self):
        self.callback.data = "set_notification_7"
        with patch.object(lists.TaskListCRUD, "get_by_id", AsyncMock(return_value=self.foreign_list)):
            await lists.set_notification_start(self.callback, self.user, self.state, self.session)
            self.state.set_state.assert_not_awaited()

    async def test_task_notification_rechecks_owner_at_submit(self):
        self.state.get_data.return_value = {"task_id": 5}
        message = SimpleNamespace(text="09:00", answer=AsyncMock())
        with patch.object(tasks.TaskCRUD, "get_by_id", AsyncMock(return_value=self.task)), \
             patch.object(tasks.TaskListCRUD, "get_by_id", AsyncMock(return_value=self.foreign_list)), \
             patch.object(tasks.TaskCRUD, "update_notification", AsyncMock()) as mutate:
            await tasks.set_task_notification_finish(message, self.session, self.state, self.user)
            mutate.assert_not_awaited()
            self.state.clear.assert_awaited_once()

    async def test_list_notification_rechecks_owner_at_submit(self):
        self.state.get_data.return_value = {"list_id": 7}
        message = SimpleNamespace(text="09:00", answer=AsyncMock())
        with patch.object(lists.TaskListCRUD, "get_by_id", AsyncMock(return_value=self.foreign_list)), \
             patch.object(lists.TaskListCRUD, "update_notification_time", AsyncMock()) as mutate:
            await lists.set_notification_finish(message, self.session, self.state, self.user)
            mutate.assert_not_awaited()
            self.state.clear.assert_awaited_once()

    async def test_cannot_add_task_to_deleted_list(self):
        self.state.get_data.return_value = {"list_id": 7}
        own_deleted = SimpleNamespace(id=7, user_id=10, is_active=False)
        message = SimpleNamespace(text="Задача", answer=AsyncMock())
        with patch.object(tasks.TaskListCRUD, "get_by_id", AsyncMock(return_value=own_deleted)), \
             patch.object(tasks.TaskCRUD, "create", AsyncMock()) as mutate:
            await tasks.add_task_finish(message, self.session, self.state, self.user)
            mutate.assert_not_awaited()

    async def test_non_text_message_does_not_crash_task_creation(self):
        message = SimpleNamespace(text=None, answer=AsyncMock())
        await tasks.add_task_finish(message, self.session, self.state, self.user)
        message.answer.assert_awaited_once()

    async def test_owner_can_configure_task(self):
        self.callback.data = "task_notify_5"
        owned_list = SimpleNamespace(id=7, user_id=10, is_active=True)
        with patch.object(tasks.TaskCRUD, "get_by_id", AsyncMock(return_value=self.task)), \
             patch.object(tasks.TaskListCRUD, "get_by_id", AsyncMock(return_value=owned_list)):
            await tasks.set_task_notification_start(self.callback, self.user, self.state, self.session)
            self.state.set_state.assert_awaited_once_with(tasks.SetTaskNotificationStates.waiting_for_time)
            self.state.update_data.assert_awaited_once_with(task_id=5)

    async def test_owner_can_toggle_task(self):
        owned_list = SimpleNamespace(id=7, user_id=10, is_active=True, name="Работа", notification_time=None)
        completed = SimpleNamespace(id=5, list_id=7, is_completed=True)
        with patch.object(tasks.TaskCRUD, "get_by_id", AsyncMock(return_value=self.task)), \
             patch.object(tasks.TaskListCRUD, "get_by_id", AsyncMock(return_value=owned_list)), \
             patch.object(tasks.TaskCRUD, "get_list_tasks", AsyncMock(return_value=[])), \
             patch.object(tasks.TaskCRUD, "toggle_complete", AsyncMock(return_value=completed)) as mutate:
            await tasks.toggle_task_status(self.callback, self.session, self.user)
            mutate.assert_awaited_once_with(self.session, 5)
            self.callback.message.edit_text.assert_awaited_once()

    async def test_owner_can_save_list_notification(self):
        self.state.get_data.return_value = {"list_id": 7}
        message = SimpleNamespace(text="9:05", answer=AsyncMock())
        owned_list = SimpleNamespace(id=7, user_id=10, is_active=True, name="Работа")
        with patch.object(lists.TaskListCRUD, "get_by_id", AsyncMock(return_value=owned_list)), \
             patch.object(lists.TaskListCRUD, "update_notification_time", AsyncMock(return_value=owned_list)) as mutate:
            await lists.set_notification_finish(message, self.session, self.state, self.user)
            mutate.assert_awaited_once_with(self.session, 7, "09:05")
            self.state.clear.assert_awaited_once()
