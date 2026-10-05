import unittest
from unittest.mock import AsyncMock

from pyasic import settings
from pyasic.web.antminer import AntminerModernWebAPI


GETTERS = (
    ("get_miner_conf", "get_miner_conf"),
    ("get_system_info", "get_system_info"),
    ("get_network_info", "get_network_info"),
    ("summary", "summary"),
    ("get_blink_status", "get_blink_status"),
)


class WebResponseCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original_setting = settings.get("antminer_web_response_cache_enabled")

    def tearDown(self):
        settings.update("antminer_web_response_cache_enabled", self.original_setting)

    async def test_enabled_caches_each_getter(self):
        settings.update("antminer_web_response_cache_enabled", True)
        for method_name, command in GETTERS:
            with self.subTest(method=method_name):
                api = AntminerModernWebAPI("192.0.2.1")
                api.send_command = AsyncMock(return_value={"value": command})
                getter = getattr(api, method_name)

                self.assertEqual(await getter(), {"value": command})
                self.assertEqual(await getter(), {"value": command})
                api.send_command.assert_awaited_once_with(command)

    async def test_disabled_fetches_each_time(self):
        settings.update("antminer_web_response_cache_enabled", False)
        for method_name, command in GETTERS:
            with self.subTest(method=method_name):
                api = AntminerModernWebAPI("192.0.2.1")
                api.send_command = AsyncMock(side_effect=[{"value": 1}, {"value": 2}])
                getter = getattr(api, method_name)

                self.assertEqual(await getter(), {"value": 1})
                self.assertEqual(await getter(), {"value": 2})
                self.assertEqual(api.send_command.await_count, 2)

    async def test_failed_response_is_not_cached(self):
        settings.update("antminer_web_response_cache_enabled", True)
        api = AntminerModernWebAPI("192.0.2.1")
        api.send_command = AsyncMock(
            side_effect=[{"success": False, "message": "error"}, {"value": 2}]
        )

        self.assertEqual((await api.summary())["success"], False)
        self.assertEqual(await api.summary(), {"value": 2})
        self.assertEqual(api.send_command.await_count, 2)

    async def test_flag_change_applies_to_existing_api(self):
        api = AntminerModernWebAPI("192.0.2.1")
        api.send_command = AsyncMock(side_effect=[{"value": 1}, {"value": 2}])

        settings.update("antminer_web_response_cache_enabled", True)
        self.assertEqual(await api.summary(), {"value": 1})
        settings.update("antminer_web_response_cache_enabled", False)
        self.assertEqual(await api.summary(), {"value": 2})
        settings.update("antminer_web_response_cache_enabled", True)
        self.assertEqual(await api.summary(), {"value": 1})
        self.assertEqual(api.send_command.await_count, 2)
