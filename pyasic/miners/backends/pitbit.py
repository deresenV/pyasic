import re

import httpx
from _testcapi import awaitType

from pyasic import settings
from pyasic.miners.backends import AntminerModern
import asyncio
import logging
from pathlib import Path

from pyasic.config import MinerConfig, MiningModeConfig
from pyasic.data import Fan, HashBoard, MinerErrorData
from pyasic.data.error_codes import X19Error
from pyasic.data.pools import PoolMetrics, PoolUrl
from pyasic.device.algorithm import AlgoHashRateType
from pyasic.errors import APIError
from pyasic.miners.backends.bmminer import BMMiner
from pyasic.miners.backends.cgminer import CGMiner
from pyasic.miners.device.firmware import PitBitFirmware
from pyasic.miners.data import (
    DataFunction,
    DataLocations,
    DataOptions,
    RPCAPICommand,
    WebAPICommand,
)
from pyasic.rpc.antminer import AntminerRPCAPI
from pyasic.ssh.antminer import AntminerModernSSH
from pyasic.web.antminer import AntminerModernWebAPI, AntminerOldWebAPI

ANTMINER_MODERN_DATA_LOC = DataLocations(
    **{
        str(DataOptions.SERIAL_NUMBER): DataFunction(
            "_get_serial_number",
            [WebAPICommand("web_get_system_info", "get_system_info")],
        ),
        str(DataOptions.MAC): DataFunction(
            "_get_mac",
            [WebAPICommand("web_get_system_info", "get_system_info")],
        ),
        str(DataOptions.API_VERSION): DataFunction(
            "_get_api_ver",
            [RPCAPICommand("rpc_version", "version")],
        ),
        str(DataOptions.FW_VERSION): DataFunction(
            "_get_fw_ver",
            [RPCAPICommand("rpc_version", "version")],
        ),
        str(DataOptions.HOSTNAME): DataFunction(
            "_get_hostname",
            [WebAPICommand("web_get_system_info", "get_system_info")],
        ),
        str(DataOptions.HASHRATE): DataFunction(
            "_get_hashrate",
            [RPCAPICommand("rpc_summary", "summary")],
        ),
        str(DataOptions.EXPECTED_HASHRATE): DataFunction(
            "_get_expected_hashrate",
            [RPCAPICommand("rpc_stats", "stats")],
        ),
        str(DataOptions.FANS): DataFunction(
            "_get_fans",
            [RPCAPICommand("rpc_stats", "stats")],
        ),
        str(DataOptions.ERRORS): DataFunction(
            "_get_errors",
            [WebAPICommand("web_summary", "summary")],
        ),
        str(DataOptions.FAULT_LIGHT): DataFunction(
            "_get_fault_light",
            [WebAPICommand("web_get_blink_status", "get_blink_status")],
        ),
        str(DataOptions.HASHBOARDS): DataFunction(
            "_get_hashboards",
            [],
        ),
        str(DataOptions.IS_MINING): DataFunction(
            "_is_mining",
            [WebAPICommand("web_get_conf", "get_miner_conf")],
        ),
        str(DataOptions.UPTIME): DataFunction(
            "_get_uptime",
            [RPCAPICommand("rpc_stats", "stats")],
        ),
        str(DataOptions.POOLS): DataFunction(
            "_get_pools",
            [RPCAPICommand("rpc_pools", "pools")],
        ),
    }
)


class PitBitMiner(PitBitFirmware, AntminerModern):
    async def _change_mining_mode(self, mining_mode: int):
        response = await self.web.set_miner_conf({"bitmain-work-mode": mining_mode, "pools": []})
        return True

    async def stop_mining(self) -> bool:
        return await self._change_mining_mode(1)

    async def resume_mining(self) -> bool:
        return await self._change_mining_mode(0)


    #todo Перенести в web класс
    async def miner_type(self):
        return await self.web.send_command("miner_type")

    async def system_info(self):
        return await self.web.send_command("get_system_info")

    async def stats(self):
        return await self.web.send_command("stats")

    async def api_conf(self):
        return await self.web.send_command("get_api_conf")

    async def serial_get(self):
        url = f"http://{self.ip}:{80}/cgi-bin_n/{"serial_get"}.cgi"
        auth = httpx.DigestAuth("root", "root")
        try:
            async with httpx.AsyncClient(transport=settings.transport()) as client:
                data = await client.get(url, auth=auth)
                return data.text
        except httpx.HTTPError as e:
            return {"success": False, "message": f"HTTP error occurred: {str(e)}"}

    async def get_uptime(self) -> int | None:
        raw_json = await self.web.send_command("stats")
        if raw_json:
            try:
                uptime = raw_json.get("STATS", {})[0].get("elapsed", 0)
                return int(uptime)
            except: pass
        return None

    async def get_wattage(self) -> int | None:
        raw_json = await self.web.send_command("stats")
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