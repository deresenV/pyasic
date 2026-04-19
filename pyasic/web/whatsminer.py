import asyncio
import re
from typing import Any
import warnings
import httpx

from pyasic import APIError
from pyasic.web.base import BaseWebAPI


class BTMinerWebAPI(BaseWebAPI):
    def __init__(self, ip: str):
        super().__init__(ip)
        self.username = "admin"
        self.password = "admin"
    async def multicommand(
        self, *commands: str, ignore_errors: bool = False, allow_warning: bool = True
    ) -> dict:
        tasks = {c: asyncio.create_task(getattr(self, c)()) for c in commands}
        await asyncio.gather(*[t for t in tasks.values()])
        return {t: tasks[t].result() for t in tasks}

    async def _get_csrf(self, client: httpx.AsyncClient):
        response = await client.get(
            url=f"https://{self.ip}/cgi-bin/luci/admin/network/btminer"
        )

        match = re.search(r'<input[^>]*name="token"[^>]*value="([^"]*)"', response.text)
        if match:
            return match.group(1)

        match = re.search(r'name="token"\s+value="([^"]*)"', response.text)
        if match:
            return match.group(1)

        return None

    async def send_command(
            self,
            command: str,
            ignore_errors: bool = False,
            allow_warning: bool = True,
            privileged: bool = False,
            **parameters: Any,
            ):
        async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
            try:
                # auth
                await client.post(
                    url=f"https://{self.ip}/cgi-bin/luci/",
                    data={
                        "luci_username": self.username,
                        "luci_password": self.password
                    }
                )
                # csrf
                csrf_token = await self._get_csrf(client)
                params = {
                    "token": csrf_token,
                    **parameters
                }
                # command
                response = await client.post(
                    url=f"https://{self.ip}/{command}",
                    data=params
                )
                if not response.status_code == 200:
                    if not ignore_errors:
                        raise APIError(f"Command failed: {command}")
                    warnings.warn(f"Command failed: {command}")
            except Exception as e:
                if ignore_errors:
                    return response.json()
                raise APIError(str(e))