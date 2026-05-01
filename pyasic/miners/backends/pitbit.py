# ------------------------------------------------------------------------------
#  Copyright 2022 Upstream Data Inc                                            -
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

from pyasic.miners.backends.antminer import AntminerModern
from pyasic.miners.data import (
    DataFunction,
    DataLocations,
    DataOptions,
    RPCAPICommand,
    WebAPICommand,
)
from pyasic.miners.device.firmware import PitBitFirmware
from pyasic.web.pitbit import PitBitWebAPI

PITBIT_DATA_LOC = DataLocations(
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
    """Handler for PitBit firmware miners."""

    _web_cls = PitBitWebAPI
    web: PitBitWebAPI

    data_locations = PITBIT_DATA_LOC

    async def _change_mining_mode(self, mining_mode: int) -> bool:
        await self.web.set_miner_conf({"bitmain-work-mode": mining_mode, "pools": []})
        return True

    async def stop_mining(self) -> bool:
        return await self._change_mining_mode(1)

    async def resume_mining(self) -> bool:
        return await self._change_mining_mode(0)

    async def get_uptime(self) -> int | None:
        data = await self.web.stats()
        if data:
            try:
                return int(data.get("STATS", {})[0].get("elapsed", 0))
            except (LookupError, TypeError, ValueError):
                pass
        return None

    async def get_wattage(self) -> int | None:
        data = await self.web.stats()
        if data:
            try:
                return int(data.get("STATS", {})[0].get("power"))
            except (LookupError, TypeError, ValueError):
                pass
        return None

