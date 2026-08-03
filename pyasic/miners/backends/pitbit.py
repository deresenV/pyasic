import asyncio
import re
from typing import Callable, Any

import httpx

from pyasic import settings
from pyasic.rpc.antminer import AntminerRPCAPI
from pyasic.web.pitbit import PitBitWebAPI
from pyasic.miners.backends import AntminerModern
from pyasic.data import HashBoard, MinerErrorData
from pyasic.data.error_codes import X19Error
from pyasic.miners.device.firmware import PitBitFirmware

class PitBitMiner(PitBitFirmware, AntminerModern):
    _web_cls = PitBitWebAPI
    web: PitBitWebAPI

    _rpc_cls = AntminerRPCAPI
    rpc: AntminerRPCAPI

    async def _change_mining_mode(self, mining_mode: int):
        try:
            try:
                config = await self.get_config()
                pools = config.as_am_modern().get("pools", [])
            except:
                pools = []
            await self.web.set_miner_conf({"bitmain-work-mode": mining_mode, "pools": pools})
            return True
        except:
            return False

    async def stop_mining(self) -> bool:
        return await self._change_mining_mode(1)

    async def resume_mining(self) -> bool:
        return await self._change_mining_mode(0)

    async def miner_type(self):
        return await self.web.miner_type()

    async def stats(self):
        tasks = [
            asyncio.create_task(self.web.stats()),
            asyncio.create_task(self.rpc.stats(True)),
        ]
        result = await self._concurrent_get_first_result(tasks, lambda x: x is not None)
        return result

    async def get_api_conf(self):
        try:
            return await self.web.get_api_conf()
        except:
            return {
                "api-remote-ctrl": True,
                "api-token": "",
                "api-url": "api.pitbit.online"
            }

    async def serial_get(self):
        url = f"http://{self.ip}:{80}/cgi-bin_n/serial_get.cgi"
        auth = httpx.DigestAuth("root", "root")
        try:
            async with httpx.AsyncClient(transport=settings.transport()) as client:
                data = await client.get(url, auth=auth)
                return data.text
        except httpx.HTTPError as e:
            return {"success": False, "message": f"HTTP error occurred: {str(e)}"}

    async def _concurrent_get_first_result(self, tasks: list, verification_func: Callable) -> Any:
        res = None
        for fut in asyncio.as_completed(tasks):
            res = await fut
            if verification_func(res):
                break
        for t in tasks:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
        return res

    async def get_uptime(self) -> int | None:
        stats = await self.stats()
        #web
        if len(stats) == 3:
            try:
                uptime = stats.get("STATS", {})[0].get("elapsed", 0)
                return int(uptime)
            except: pass
        #rpc
        elif len(stats) == 2:
            try:
                uptime = stats.get("STATS", [{}, {}])[1].get("Elapsed", 0)
                return int(uptime)
            except:
                pass
        return None


    async def get_wattage(self) -> int | None:
        # In rpc stats no data about power wattage
        raw_json = await self.web.stats()
        if raw_json:
            try:
                power = raw_json.get("STATS", {})[0].get("power")
                return int(power)
            except:
                pass
        return None

    async def get_hashboards_from_logs(self, hashboards):
        log_pattern = re.compile(r"Detected (?P<chips>\d+) chips .* on chain (?P<chain>\d+)")
        hashboards_from_logs = await self._parse_pattern_logs(pattern=log_pattern)
        if len(hashboards_from_logs)>0:
            for chain in hashboards_from_logs:
                try:
                    hashboards[int(chain.get("chain", 0))].chips = int(chain.get("chips", 0))
                except IndexError:
                    try:
                        hashboards.append(HashBoard(slot=int(chain.get("chain")), chips=int(chain.get("chips")), expected_chips=self.expected_chips))
                    except:pass
                except Exception as e:
                    pass
        return hashboards

    async def get_errors(self) -> list[MinerErrorData]:
        errors = await super().get_errors()
        pattern = re.compile(r"\[(?P<level>\w+)\]\s+[\d-]+\s+[\d:.]+\s+\w+\s+(?P<msg>.*)")
        errors_from_log = await self._parse_pattern_logs(target_patterns={"Cannot detect power version!"}, pattern=pattern)
        if len(errors_from_log)>0:
            for error in errors_from_log:
                errors.append(X19Error(error_message=f"{" ".join(value for value in error.values())}"))
        return errors

    async def get_hashboards(self) -> list[HashBoard]:
        hashboards = await super().get_hashboards()
        if len(hashboards) != self.expected_hashboards:
            hashboards_from_log= await self.get_hashboards_from_logs(hashboards)
            if hashboards_from_log:
                return hashboards_from_log
        return hashboards

    async def _get_fw_ver(self, rpc_version: dict | None = None) -> str | None:
        miner_type = await self.web.miner_type()
        fw_raw = miner_type.get("miner_type", "").split("(")
        fw = fw_raw[1].replace(")", "")
        return fw

    async def get_fw_ver(self) -> str | None:
        return await self._get_fw_ver()

    async def set_cloud_token(self, token: str):
        current_api_settings = await self.get_api_conf()
        current_api_settings["api-token"] = token
        return await self.web.set_cloud_token(current_api_settings)

    async def get_cloud_token(self) -> str | None:
        current_api_settings = await self.get_api_conf()
        return current_api_settings.get("api-token", None)