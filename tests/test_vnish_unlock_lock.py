import asyncio
import unittest
from unittest.mock import patch

import httpx

from pyasic import settings
from pyasic.web.vnish import VNishWebAPI


class VNishUnlockLockTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_commands_share_initial_unlock(self):
        unlocks = 0

        async def handler(request):
            nonlocal unlocks
            if request.url.path == "/api/v1/unlock":
                unlocks += 1
                await asyncio.sleep(0.01)
                return httpx.Response(200, json={"token": "fresh"})
            self.assertEqual(request.headers["Authorization"], "fresh")
            return httpx.Response(200, json={"ok": True})

        with patch.object(settings, "transport", return_value=httpx.MockTransport(handler)):
            api = VNishWebAPI("192.0.2.1")
            results = await asyncio.gather(
                api.info(), api.settings(), api.chips()
            )

        self.assertEqual(unlocks, 1)
        self.assertEqual(results, [{"ok": True}] * 3)

    async def test_concurrent_expired_token_refreshes_once(self):
        unlocks = 0
        old_retries = settings.get("get_data_retries")
        settings.update("get_data_retries", 2)

        async def handler(request):
            nonlocal unlocks
            if request.url.path == "/api/v1/unlock":
                unlocks += 1
                await asyncio.sleep(0.01)
                return httpx.Response(200, json={"token": "fresh"})
            if request.headers["Authorization"] == "stale":
                return httpx.Response(401)
            return httpx.Response(200, json={"ok": True})

        try:
            with patch.object(settings, "transport", return_value=httpx.MockTransport(handler)):
                api = VNishWebAPI("192.0.2.1")
                api.token = "stale"
                results = await asyncio.gather(
                    api.info(), api.settings(), api.chips()
                )
        finally:
            settings.update("get_data_retries", old_retries)

        self.assertEqual(unlocks, 1)
        self.assertEqual(results, [{"ok": True}] * 3)
