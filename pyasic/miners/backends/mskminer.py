from http.client import responses

from pyasic import APIError, MinerConfig
from pyasic.config import PoolConfig
from pyasic.device.algorithm import AlgoHashRateType
from pyasic.miners.backends import BMMiner
from pyasic.miners.data import (
    DataFunction,
    DataLocations,
    DataOptions,
    RPCAPICommand,
    WebAPICommand,
)
from pyasic.config.pools import Pool, PoolGroup
from pyasic.miners.device.firmware import MSKMinerFirmware
from pyasic.web.mskminer import MSKMinerWebAPI

MSKMINER_DATA_LOC = DataLocations(
    **{
        str(DataOptions.API_VERSION): DataFunction(
            "_get_api_ver",
            [RPCAPICommand("rpc_version", "version")],
        ),
        str(DataOptions.FW_VERSION): DataFunction(
            "_get_fw_ver",
            [RPCAPICommand("rpc_version", "version")],
        ),
        str(DataOptions.MAC): DataFunction(
            "_get_mac",
            [WebAPICommand("web_info_v1", "info_v1")],
        ),
        str(DataOptions.HASHRATE): DataFunction(
            "_get_hashrate",
            [RPCAPICommand("rpc_stats", "stats")],
        ),
        str(DataOptions.EXPECTED_HASHRATE): DataFunction(
            "_get_expected_hashrate",
            [RPCAPICommand("rpc_stats", "stats")],
        ),
        str(DataOptions.HASHBOARDS): DataFunction(
            "_get_hashboards",
            [RPCAPICommand("rpc_stats", "stats")],
        ),
        str(DataOptions.WATTAGE): DataFunction(
            "_get_wattage",
            [RPCAPICommand("rpc_stats", "stats")],
        ),
        str(DataOptions.FANS): DataFunction(
            "_get_fans",
            [RPCAPICommand("rpc_stats", "stats")],
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


class MSKMiner(MSKMinerFirmware, BMMiner):
    """Handler for MSKMiner"""

    data_locations = MSKMINER_DATA_LOC

    web: MSKMinerWebAPI
    _web_cls = MSKMinerWebAPI

    async def _get_hashrate(
        self, rpc_stats: dict | None = None
    ) -> AlgoHashRateType | None:
        # get hr from API
        if rpc_stats is None:
            try:
                rpc_stats = await self.rpc.stats()
            except APIError:
                pass
        if rpc_stats is not None:
            try:
                return self.algo.hashrate(
                    rate=float(rpc_stats["STATS"][1]["GHS 5s"]),
                    unit=self.algo.unit.GH,  # type: ignore[attr-defined]
                ).into(
                    self.algo.unit.default  # type: ignore[attr-defined]
                )
            except (LookupError, ValueError, TypeError):
                pass
        return None

    async def blink(self, command: str) -> bool:
        try:
            answer = await self.web.send_command(command)
            if answer:
                return answer['ok']
        except:
            pass
        return False


    async def reboot(self) -> bool:
        answer = None
        try:
            answer = await self.web.send_command("reboot")
            return True
        except:
            pass
        return False

    async def fault_light_on(self) -> bool:
        return await self.blink("blink/start")


    async def fault_light_off(self) -> bool:
        """All miners return False if command success"""
        if await self.blink("blink/stop"):
            return False
        return True

    async def _get_wattage(self, rpc_stats: dict | None = None) -> int | None:
        if rpc_stats is None:
            try:
                rpc_stats = await self.rpc.stats()
            except APIError:
                pass

        if rpc_stats is not None:
            try:
                return rpc_stats["STATS"][0]["total_power"]
            except (LookupError, ValueError, TypeError):
                pass
        return None

    async def _get_mac(self, web_info_v1: dict | None = None) -> str | None:
        if web_info_v1 is None:
            try:
                web_info_v1 = await self.web.info_v1()
            except APIError:
                pass

        if web_info_v1 is not None:
            try:
                return web_info_v1["network_info"]["result"]["macaddr"].upper()
            except (LookupError, ValueError, TypeError):
                pass
        return None


    async def send_config(
        self, config: MinerConfig, user_suffix: str | None = None
    ) -> None:
        return await self.web.set_miner_conf(config)

    async def get_config(self) -> MinerConfig:
        miner_data = await self.web.info_app()
        raw_pools = miner_data.get("pools")
        pools = []
        for pool in raw_pools:
            url = pool.get("url", None)
            user = pool.get("user", None)
            password = pool.get("pass", None)
            pools.append(Pool(url=url, user=user, password=password))
        miner_config = MinerConfig(pools=PoolConfig(groups = [PoolGroup(pools=pools)]))
        return miner_config


    async def get_fault_light(self) -> bool:
        info_app = await self.web.info_app()
        return info_app.get("blink", False)


    async def resume_mining(self) -> bool:
        try:
            response = await self.web.send_command("miner_resume")
            return True
        except:
            return False

    async def stop_mining(self) -> bool:
        try:
            response = await self.web.send_command("miner_pause")
            return True
        except:
            return False

    async def _get_voltage(self) -> float | None:
        response = await self.web.send_get_command("tune/v2/current")
        try:
            if not response:
                return None
            current_params = response.get('params')
            if current_params:
                if int(current_params.get("tune_type", 1)) == 0:
                    current_profile = current_params.get("tune_profile", 0)
                    return 2000 + int(current_profile)*100
            return None
        except:
            return None


    async def get_voltage(self) -> float | None:
        return await self._get_voltage()

    async def set_power_limit(self, wattage: int) -> bool:
        power_id = 0 - (2000 - wattage) // 100
        payload = {
            "profile_id": power_id,
            "profile_type": "power",
            "set_preset_without_tune": True,
            "tune_eff": False
        }
        response = await self.web.send_command("tune/v3/apply", False, True,False, **payload)
        return True
