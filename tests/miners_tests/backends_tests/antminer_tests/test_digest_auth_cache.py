import asyncio
import unittest
from unittest.mock import patch

import httpx

from pyasic import settings
from pyasic.errors import APIError
from pyasic.web.antminer import AntminerModernWebAPI


class DigestAuthCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original_setting = settings.get("antminer_digest_auth_cache_enabled")

    def tearDown(self):
        settings.update("antminer_digest_auth_cache_enabled", self.original_setting)

    async def test_port_6060_accepts_extra_spaces_in_status_line(self):
        settings.update("antminer_digest_auth_cache_enabled", True)
        requests = []

        async def handle(reader, writer):
            request = await reader.readuntil(b"\r\n\r\n")
            requests.append(request)
            if b"Authorization: Digest " in request:
                writer.write(
                    b"HTTP/1.0  200  OK\r\n"
                    b"Content-Length: 14\r\n\r\nminer power:23"
                )
            else:
                writer.write(
                    b"HTTP/1.0 401 Unauthorized\r\n"
                    b'WWW-Authenticate: Digest realm="miner", nonce="one", qop="auth"\r\n'
                    b"Content-Length: 0\r\n\r\n"
                )
            await writer.drain()
            writer.close()

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        async with server:
            api = AntminerModernWebAPI("127.0.0.1")
            api.port_6060 = server.sockets[0].getsockname()[1]
            self.assertEqual(await api.send_6060_command("miner_power"), "miner power:23")

        self.assertEqual(len(requests), 2)

    async def test_enabled_reuses_challenge_across_methods(self):
        settings.update("antminer_digest_auth_cache_enabled", True)
        requests = []

        def handler(request):
            requests.append((request.url.path, request.headers.get("authorization")))
            if "authorization" not in request.headers:
                return httpx.Response(
                    401,
                    headers={
                        "WWW-Authenticate": 'Digest realm="miner", nonce="one", qop="auth"'
                    },
                )
            if request.url.path.endswith("log.cgi"):
                return httpx.Response(200, text="miner log")
            return httpx.Response(200, json={"ok": True})

        with patch.object(settings, "transport", return_value=httpx.MockTransport(handler)):
            api = AntminerModernWebAPI("192.0.2.1")
            result = await api.multicommand("summary", "stats")
            logs = await api.get_logs()
            direct = await api.send_command("get_miner_conf")

        self.assertEqual(result["summary"], {"ok": True})
        self.assertEqual(result["stats"], {"ok": True})
        self.assertEqual(logs, "miner log")
        self.assertEqual(direct, {"ok": True})
        self.assertEqual(sum(auth is None for _, auth in requests), 1)

    async def test_disabled_uses_fresh_challenge_for_each_request(self):
        settings.update("antminer_digest_auth_cache_enabled", False)
        requests = []

        def handler(request):
            requests.append(request.headers.get("authorization"))
            if "authorization" not in request.headers:
                return httpx.Response(
                    401,
                    headers={
                        "WWW-Authenticate": 'Digest realm="miner", nonce="one", qop="auth"'
                    },
                )
            return httpx.Response(200, json={"ok": True})

        with patch.object(settings, "transport", return_value=httpx.MockTransport(handler)):
            api = AntminerModernWebAPI("192.0.2.1")
            await api.send_command("summary")
            await api.send_command("stats")

        self.assertEqual(sum(auth is None for auth in requests), 2)

    async def test_expired_challenge_is_refreshed(self):
        settings.update("antminer_digest_auth_cache_enabled", True)
        challenges = []
        nonce_rotated = False

        def handler(request):
            auth = request.headers.get("authorization", "")
            if 'nonce="two"' in auth:
                return httpx.Response(200, json={"ok": True})
            if 'nonce="one"' in auth:
                if nonce_rotated:
                    challenges.append("two")
                    return httpx.Response(
                        401,
                        headers={
                            "WWW-Authenticate": 'Digest realm="miner", nonce="two", qop="auth"'
                        },
                    )
                return httpx.Response(200, json={"ok": True})
            challenges.append("one")
            return httpx.Response(
                401,
                headers={
                    "WWW-Authenticate": 'Digest realm="miner", nonce="one", qop="auth"'
                },
            )

        with patch.object(settings, "transport", return_value=httpx.MockTransport(handler)):
            api = AntminerModernWebAPI("192.0.2.1")
            self.assertEqual(await api.send_command("summary"), {"ok": True})
            nonce_rotated = True
            result = await api.send_command("stats")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(challenges, ["one", "two"])

    async def test_setting_changes_apply_to_existing_api(self):
        requests = []

        def handler(request):
            requests.append(request.headers.get("authorization"))
            if "authorization" not in request.headers:
                return httpx.Response(
                    401,
                    headers={
                        "WWW-Authenticate": 'Digest realm="miner", nonce="one", qop="auth"'
                    },
                )
            return httpx.Response(200, json={"ok": True})

        with patch.object(settings, "transport", return_value=httpx.MockTransport(handler)):
            api = AntminerModernWebAPI("192.0.2.1")
            settings.update("antminer_digest_auth_cache_enabled", True)
            await api.send_command("summary")
            settings.update("antminer_digest_auth_cache_enabled", False)
            await api.send_command("stats")
            settings.update("antminer_digest_auth_cache_enabled", True)
            await api.send_command("get_miner_conf")

        self.assertEqual(sum(auth is None for auth in requests), 2)

    async def test_port_6060_reuses_web_digest_challenge(self):
        settings.update("antminer_digest_auth_cache_enabled", True)
        requests = []

        def handler(request):
            requests.append((request.url.port, request.url.path, request.headers.get("authorization")))
            if "authorization" not in request.headers:
                return httpx.Response(
                    401,
                    headers={
                        "WWW-Authenticate": 'Digest realm="miner", nonce="one", qop="auth"'
                    },
                )
            if request.url.port == 6060:
                return httpx.Response(200, text="miner power:23")
            return httpx.Response(200, json={"ok": True})

        with patch.object(settings, "transport", return_value=httpx.MockTransport(handler)):
            api = AntminerModernWebAPI("192.0.2.1")
            await api.send_command("summary")
            result = await api.send_6060_command("miner_power")

        self.assertEqual(result, "miner power:23")
        self.assertEqual(api.port_6060, 6060)
        self.assertEqual(requests[-1][:2], (6060, "/miner_power"))
        self.assertIsNotNone(requests[-1][2])
        self.assertEqual(sum(auth is None for _, _, auth in requests), 1)

    async def test_port_6060_refreshes_different_challenge(self):
        settings.update("antminer_digest_auth_cache_enabled", True)
        requests = []

        def handler(request):
            auth = request.headers.get("authorization", "")
            requests.append((request.url.port, auth))
            nonce = "two" if request.url.port == 6060 else "one"
            if f'nonce="{nonce}"' not in auth:
                return httpx.Response(
                    401,
                    headers={
                        "WWW-Authenticate": f'Digest realm="miner", nonce="{nonce}", qop="auth"'
                    },
                )
            if request.url.port == 6060:
                return httpx.Response(200, text="miner power:23")
            return httpx.Response(200, json={"ok": True})

        with patch.object(settings, "transport", return_value=httpx.MockTransport(handler)):
            api = AntminerModernWebAPI("192.0.2.1")
            self.assertEqual(await api.send_command("summary"), {"ok": True})
            self.assertEqual(await api.send_6060_command("miner_power"), "miner power:23")
            self.assertEqual(await api.send_command("stats"), {"ok": True})

        self.assertEqual(len(requests), 6)

    async def test_port_6060_reports_http_error(self):
        settings.update("antminer_digest_auth_cache_enabled", False)
        requests = []

        def handler(request):
            requests.append(request.headers.get("authorization"))
            if "authorization" not in request.headers:
                return httpx.Response(
                    401,
                    headers={
                        "WWW-Authenticate": 'Digest realm="miner", nonce="one", qop="auth"'
                    },
                )
            return httpx.Response(404)

        with patch.object(settings, "transport", return_value=httpx.MockTransport(handler)):
            api = AntminerModernWebAPI("192.0.2.1")
            with self.assertRaises(APIError):
                await api.send_6060_command("/unknown")

        self.assertEqual(len(requests), 2)
