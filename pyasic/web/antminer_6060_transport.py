"""Compatibility transport for malformed HTTP status lines on Antminer port 6060."""

from __future__ import annotations

import re
import ssl
from typing import Any

import httpcore
import httpx


_STATUS_LINE = re.compile(rb"^(HTTP/1\.[01])[ \t]+([0-9]{3})(?:[ \t]+(.*))?$", re.DOTALL)


class _StatusLineStream(httpcore.AsyncNetworkStream):
    def __init__(self, stream: httpcore.AsyncNetworkStream) -> None:
        self._stream = stream
        self._pending = bytearray()
        self._first_read = True

    async def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        if self._first_read:
            while b"\n" not in self._pending and len(self._pending) < 8192:
                chunk = await self._stream.read(max_bytes, timeout=timeout)
                if not chunk:
                    break
                self._pending.extend(chunk)
            self._first_read = False
            line, separator, rest = bytes(self._pending).partition(b"\n")
            match = _STATUS_LINE.fullmatch(line.rstrip(b"\r")) if separator else None
            if match:
                reason = match.group(3)
                normalized = match.group(1) + b" " + match.group(2)
                if reason:
                    normalized += b" " + reason.strip()
                self._pending = bytearray(normalized + b"\r\n" + rest)
        if self._pending:
            result = bytes(self._pending[:max_bytes])
            del self._pending[:max_bytes]
            return result
        return await self._stream.read(max_bytes, timeout=timeout)

    async def write(self, buffer: bytes, timeout: float | None = None) -> None:
        if not self._pending:
            self._first_read = True
        await self._stream.write(buffer, timeout=timeout)

    async def aclose(self) -> None:
        await self._stream.aclose()

    async def start_tls(
        self,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> httpcore.AsyncNetworkStream:
        stream = await self._stream.start_tls(ssl_context, server_hostname, timeout)
        return _StatusLineStream(stream)

    def get_extra_info(self, info: str) -> Any:
        return self._stream.get_extra_info(info)


class _StatusLineBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, backend: httpcore.AsyncNetworkBackend) -> None:
        self._backend = backend

    async def connect_tcp(self, *args: Any, **kwargs: Any) -> httpcore.AsyncNetworkStream:
        return _StatusLineStream(await self._backend.connect_tcp(*args, **kwargs))

    async def connect_unix_socket(self, *args: Any, **kwargs: Any) -> httpcore.AsyncNetworkStream:
        return _StatusLineStream(await self._backend.connect_unix_socket(*args, **kwargs))

    async def sleep(self, seconds: float) -> None:
        await self._backend.sleep(seconds)


def tolerate_6060_status_line(transport: httpx.AsyncBaseTransport) -> httpx.AsyncBaseTransport:
    """Normalize only the status line, before httpcore parses the response."""
    if isinstance(transport, httpx.AsyncHTTPTransport):
        # HTTPX does not expose a network-backend hook. Keep this private
        # adjustment confined to the short-lived port 6060 transport.
        pool = transport._pool
        pool._network_backend = _StatusLineBackend(pool._network_backend)
    return transport
