# ------------------------------------------------------------------------------
#  Copyright 2024 Upstream Data Inc                                            -
#                                                                              -
#  Licensed under the Apache License, Version 2.0 (the "License");             -
#  you may not use this file except in compliance with the License.            -
#  You may obtain a copy of the License at                                     -
#                                                                              -
#      http://www.apache.org/licenses/LICENSE-2.0                              -
#                                                                              -
#  Unless required by applicable law or agreed to in writing, software         -
#  distributed under the License is distributed on an "AS IS" BASIS,           -
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.    -
#  See the License for the specific language governing permissions and         -
#  limitations under the License.                                              -
# ------------------------------------------------------------------------------
from __future__ import annotations

import asyncio
import warnings
from typing import Any

import httpx

from pyasic import settings, MinerConfig
from pyasic.errors import APIError
from pyasic.web.base import BaseWebAPI


class MSKMinerWebAPI(BaseWebAPI):
    def __init__(self, ip: str) -> None:
        super().__init__(ip)
        self._info_app = None
        self.username = "root"
        self.pwd = "root"


    async def multicommand(
        self, *commands: str, ignore_errors: bool = False, allow_warning: bool = True
    ) -> dict:
        tasks = {c: asyncio.create_task(getattr(self, c)()) for c in commands}
        await asyncio.gather(*[t for t in tasks.values()])
        return {t: tasks[t].result() for t in tasks}

    async def send_command(
        self,
        command: str,
        ignore_errors: bool = False,
        allow_warning: bool = True,
        privileged: bool = False,
        **parameters: Any,
    ) -> dict:
        async with httpx.AsyncClient(transport=settings.transport()) as client:
            try:
                # auth
                await client.post(
                    f"http://{self.ip}:{self.port}/admin/login",
                    data={"username": self.username, "password": self.pwd},
                )
            except httpx.HTTPError:
                warnings.warn(f"Could not authenticate with miner web: {self}")
            try:
                resp = await client.post(
                    f"http://{self.ip}:{self.port}/api/{command}", json=parameters, timeout=10
                )
                if not resp.status_code == 200:
                    if not ignore_errors:
                        raise APIError(f"Command failed: {command}")
                    warnings.warn(f"Command failed: {command}")
                return resp.json()
            except httpx.HTTPError:
                raise APIError(f"Command failed: {command}")

    async def send_get_command(self,
                               command: str,
                               ignore_errors: bool = False
    ) -> dict:
        async with httpx.AsyncClient(transport=settings.transport()) as client:
            try:
                # auth
                await client.post(
                    f"http://{self.ip}:{self.port}/admin/login",
                    data={"username": self.username, "password": self.pwd},
                )
            except httpx.HTTPError:
                warnings.warn(f"Could not authenticate with miner web: {self}")
            try:
                resp = await client.get(
                    f"http://{self.ip}:{self.port}/api/{command}"
                )
                if not resp.status_code == 200:
                    if not ignore_errors:
                        raise APIError(f"Command failed: {command}")
                    warnings.warn(f"Command failed: {command}")
                return resp.json()
            except httpx.HTTPError:
                raise APIError(f"Command failed: {command}")

    async def info_v1(self):
        return await self.send_command("info_v1")

    async def info_app(self) -> dict:
        if not self._info_app:
            self._info_app = await self.send_get_command("info_app")
        return self._info_app

    #todo вынести логику в другие общие функции
    async def set_miner_conf(self, config: MinerConfig):
        pools_data = []
        for p in config.pools.groups[0].pools:
            pools_data.append({
                "url": p.url,
                "user": p.user,
                "pass": p.password
            })

        while len(pools_data) < 3:
            pools_data.append({"url": "", "user": "", "pass": ""})

        payload = {"pools": pools_data}

        async with httpx.AsyncClient(transport=settings.transport()) as client:
            try:
                await client.post(
                    f"http://{self.ip}:{self.port}/admin/login",
                    data={"username": self.username, "password": self.pwd},
                )
            except httpx.HTTPError:
                warnings.warn(f"Could not authenticate with miner web: {self}")

            try:
                resp = await client.post(
                    f"http://{self.ip}:{self.port}/api/miner_settings",
                    json=payload
                )

                if resp.status_code != 200:
                    raise APIError(f"Command failed: miner_settings. Status: {resp.status_code}")

                return resp.json()
            except httpx.HTTPError as e:
                raise APIError(f"HTTP error occurred: {e}")

    async def temp(self) -> dict:
        info_app = await self.info_app()
        return info_app.get("temp", {})

    async def power(self) -> int | None:
        info_app = await self.info_app()
        return info_app.get("power", None)

    async def tune_v2_current(self) -> int:
        miner_data = await self.info_app()
        current = miner_data.get("tune_profile")
        try:
            return current.split()[0]
        except:
            return 0

    async def miner_pause(self) -> bool:
        try:
            await self.send_command("miner_pause")
            return True
        except:
            return False

    async def miner_resume(self) -> bool:
        try:
            await self.send_command("miner_resume")
            return True
        except:
            return False

    async def blink_status(self):
        info_app = await self.info_app()
        return info_app.get("blink", False)

    async def pools(self) -> list:
        miner_data = await self.info_app()
        return miner_data.get("pools", [])

    async def advanced_config(self) -> dict:
        info_app = await self.info_app()
        return info_app.get("adv_config", {}).get("all", [])

    async def is_overheat(self):
        miner_data = await self.info_app()
        overheat = miner_data.get("is_overheat", False)
        # overheat = await self.send_get_command("overheat/is_overheat")
        return overheat

    async def uptime(self) -> str | None:
        info_app = await self.info_app()
        return info_app.get("running_time", None)

    async def overheat_stop(self) -> bool:
        try:
            await self.send_command("overheat/stop")
            return True
        except:
            return False

    async def set_cloud_token(self, token: str):
        try:
            response = await self.send_command("cloud_stat/connect", **{"token": token})
            return response.get("success", False)
        except Exception:
            return False