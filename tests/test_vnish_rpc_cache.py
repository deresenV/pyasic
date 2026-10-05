import asyncio
import unittest
from unittest.mock import AsyncMock

from pyasic import settings
from pyasic.miners.backends.vnish import VNish
from pyasic.rpc.bmminer import BMMinerRPCAPI
from pyasic.rpc.vnish import VNishRPCAPI


class VNishRPCStatsCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original_setting = settings.get("rpc_response_cache_enabled")

    def tearDown(self):
        settings.update("rpc_response_cache_enabled", self.original_setting)

    async def test_vnish_uses_dedicated_rpc_class(self):
        self.assertIs(VNish._rpc_cls, VNishRPCAPI)
        self.assertTrue(issubclass(VNishRPCAPI, BMMinerRPCAPI))
        self.assertIsInstance(VNish("192.0.2.1").rpc, VNishRPCAPI)

    async def test_concurrent_stats_use_one_rpc_request(self):
        settings.update("rpc_response_cache_enabled", True)
        api = VNishRPCAPI("192.0.2.1")

        async def fetch(command):
            await asyncio.sleep(0.01)
            return {"STATS": [{"value": 1}]}

        api.send_command = AsyncMock(side_effect=fetch)
        results = await asyncio.gather(*(api.stats() for _ in range(4)))

        self.assertEqual(api.send_command.await_count, 1)
        api.send_command.assert_awaited_once_with("stats")
        self.assertEqual(results, [{"STATS": [{"value": 1}]}] * 4)
        self.assertEqual(await api.stats(), results[0])

    async def test_disabled_cache_issues_separate_requests(self):
        settings.update("rpc_response_cache_enabled", False)
        api = VNishRPCAPI("192.0.2.1")

        async def fetch(command):
            await asyncio.sleep(0.01)
            return {"STATS": []}

        api.send_command = AsyncMock(side_effect=fetch)
        await asyncio.gather(*(api.stats() for _ in range(4)))

        self.assertEqual(api.send_command.await_count, 4)

    async def test_failure_is_not_cached(self):
        settings.update("rpc_response_cache_enabled", True)
        api = VNishRPCAPI("192.0.2.1")
        api.send_command = AsyncMock(
            side_effect=[{"success": False}, {"STATS": [{"value": 2}]}]
        )

        self.assertEqual(await api.stats(), {"success": False})
        self.assertEqual(await api.stats(), {"STATS": [{"value": 2}]})
        self.assertEqual(api.send_command.await_count, 2)
