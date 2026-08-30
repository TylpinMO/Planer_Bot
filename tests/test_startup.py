import unittest
from unittest.mock import AsyncMock, patch

import main
from services.payments import PaymentService


class StartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_bot_reaches_polling_without_network(self):
        # Dummy value only; every Telegram network operation is replaced below.
        with patch.object(type(main.config), "BOT_TOKEN", "123456:offline-test"), \
             patch.object(type(main.config), "ADMIN_IDS", [1]), \
             patch.object(main, "init_db", AsyncMock()), \
             patch.object(main, "register_handlers"), \
             patch.object(main, "NotificationService"), \
             patch.object(main.Bot, "delete_webhook", AsyncMock()), \
             patch.object(main.Dispatcher, "start_polling", AsyncMock()) as poll:
            await main.main()
            poll.assert_awaited_once()

    def test_payment_payload_and_amount_are_checked(self):
        data = PaymentService.get_premium_invoice_data()
        price = data["prices"][0].amount
        self.assertTrue(PaymentService.validate_payment(data["payload"], price))
        self.assertFalse(PaymentService.validate_payment("unexpected", price))
        self.assertFalse(PaymentService.validate_payment(data["payload"], price + 1))
