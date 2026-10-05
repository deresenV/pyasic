import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from pyasic import settings
from pyasic.rpc.antminer import AntminerRPCAPI
from pyasic.rpc.btminer import BTMinerRPCAPI, BTMinerV3RPCAPI
from pyasic.web.mskminer import MSKMinerWebAPI
from pyasic.web.pitbit import PitBitWebAPI
from pyasic.web.vnish import VNishWebAPI


class ResponseCacheFlagTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original_web = settings.get("web_response_cache_enabled")
        self.original_rpc = settings.get("rpc_response_cache_enabled")

    def tearDown(self):
        settings.update("web_response_cache_enabled", self.original_web)
        settings.update("rpc_response_cache_enabled", self.original_rpc)

    async def test_web_getters_respect_flag(self):
        cases = (
            (VNishWebAPI, "summary", "send_command"),
            (VNishWebAPI, "perf_summary", "send_command"),
            (VNishWebAPI, "status", "send_command"),
            (MSKMinerWebAPI, "info_app", "send_get_command"),
            (PitBitWebAPI, "stats", "send_command"),
        )
        for cls, method_name, sender_name in cases:
            with self.subTest(cls=cls.__name__, method=method_name):
                api = cls("192.0.2.1")
                sender = AsyncMock(side_effect=[{"value": 1}, {"value": 2}])
                setattr(api, sender_name, sender)
                getter = getattr(api, method_name)

                settings.update("web_response_cache_enabled", True)
                self.assertEqual(await getter(), {"value": 1})
                self.assertEqual(await getter(), {"value": 1})
                settings.update("web_response_cache_enabled", False)
                self.assertEqual(await getter(), {"value": 2})
                self.assertEqual(sender.await_count, 2)

    async def test_msk_logs_respect_flag(self):
        api = MSKMinerWebAPI("192.0.2.1")
        api.send_get_command = AsyncMock(
            side_effect=[{"text": "first"}, {"text": "second"}]
        )
        settings.update("web_response_cache_enabled", True)
        self.assertEqual(await api.get_logs(), "first")
        self.assertEqual(await api.get_logs(), "first")
        settings.update("web_response_cache_enabled", False)
        self.assertEqual(await api.get_logs(), "second")

    async def test_pitbit_api_conf_respects_flag(self):
        calls = 0

        def handler(request):
            nonlocal calls
            calls += 1
            return httpx.Response(200, json={"value": calls})

        api = PitBitWebAPI("192.0.2.1")
        with patch.object(settings, "transport", return_value=httpx.MockTransport(handler)):
            settings.update("web_response_cache_enabled", True)
            self.assertEqual(await api.get_api_conf(), {"value": 1})
            self.assertEqual(await api.get_api_conf(), {"value": 1})
            settings.update("web_response_cache_enabled", False)
            self.assertEqual(await api.get_api_conf(), {"value": 2})

    async def test_rpc_getters_respect_flag(self):
        cases = (
            (BTMinerRPCAPI, "summary"),
            (BTMinerRPCAPI, "devdetails"),
            (BTMinerRPCAPI, "status"),
            (BTMinerRPCAPI, "get_miner_info"),
            (BTMinerV3RPCAPI, "get_miner_status_summary"),
            (BTMinerV3RPCAPI, "get_miner_status_edevs"),
            (BTMinerV3RPCAPI, "get_miner_status_pools"),
            (BTMinerV3RPCAPI, "get_miner_setting"),
            (BTMinerV3RPCAPI, "get_device_info"),
        )
        for cls, method_name in cases:
            with self.subTest(cls=cls.__name__, method=method_name):
                api = cls("192.0.2.1")
                api.send_command = AsyncMock(
                    side_effect=[{"value": 1}, {"value": 2}]
                )
                getter = getattr(api, method_name)

                settings.update("rpc_response_cache_enabled", True)
                self.assertEqual(await getter(), {"value": 1})
                self.assertEqual(await getter(), {"value": 1})
                settings.update("rpc_response_cache_enabled", False)
                self.assertEqual(await getter(), {"value": 2})
                self.assertEqual(api.send_command.await_count, 2)

    async def test_antminer_stats_keeps_api_versions_separate(self):
        api = AntminerRPCAPI("192.0.2.1")
        api.send_command = AsyncMock(side_effect=[{"old": 1}, {"new": 1}, {"old": 2}])
        settings.update("rpc_response_cache_enabled", True)
        self.assertEqual(await api.stats(), {"old": 1})
        self.assertEqual(await api.stats(new_api=True), {"new": 1})
        self.assertEqual(await api.stats(), {"old": 1})
        settings.update("rpc_response_cache_enabled", False)
        self.assertEqual(await api.stats(), {"old": 2})

    async def test_failed_response_is_not_cached(self):
        api = BTMinerRPCAPI("192.0.2.1")
        api.send_command = AsyncMock(
            side_effect=[{"success": False}, {"value": 2}]
        )
        settings.update("rpc_response_cache_enabled", True)
        self.assertEqual(await api.summary(), {"success": False})
        self.assertEqual(await api.summary(), {"value": 2})

    async def test_concurrent_antminer_stats_share_one_rpc_request(self):
        api = AntminerRPCAPI("192.0.2.1")
        calls = 0

        async def fetch(*args, **kwargs):
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.01)
            return {"STATS": [{"value": calls}]}

        api.send_command = AsyncMock(side_effect=fetch)
        settings.update("rpc_response_cache_enabled", True)
        results = await asyncio.gather(*(api.stats() for _ in range(4)))

        self.assertEqual(calls, 1)
        self.assertEqual(results, [{"STATS": [{"value": 1}]}] * 4)

    async def test_concurrent_stats_without_cache_still_fetch_separately(self):
        api = AntminerRPCAPI("192.0.2.1")
        calls = 0

        async def fetch(*args, **kwargs):
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.01)
            return {"STATS": [{"value": calls}]}

        api.send_command = AsyncMock(side_effect=fetch)
        settings.update("rpc_response_cache_enabled", False)
        await asyncio.gather(*(api.stats() for _ in range(4)))

        self.assertEqual(calls, 4)
