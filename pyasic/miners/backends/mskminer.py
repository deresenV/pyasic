from http.client import responses

from pyasic import APIError, MinerConfig
from pyasic.config import PoolConfig, FanModeType, FanModeConfig, FanModeNormal
from pyasic.data import HashBoard
from pyasic.data.network import NetworkConfig
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
        raw_pools = await self.web.pools()
        raw_config = await self.web.advanced_config()
        minimum_fans = raw_config.get("min-fan-num", None)
        if minimum_fans:
            fan_mode = FanModeNormal(minimum_fans=minimum_fans)
        else:
            fan_mode = FanModeConfig.default()
        pools = []
        for pool in raw_pools:
            url = pool.get("url", None)
            user = pool.get("user", None)
            password = pool.get("pass", None)
            pools.append(Pool(url=url, user=user, password=password))

        miner_config = MinerConfig(pools=PoolConfig(groups = [PoolGroup(pools=pools)]), fan_mode=fan_mode)
        return miner_config


    async def get_fault_light(self) -> bool:
        return await self.web.blink_status()

    async def resume_mining(self) -> bool:
        return await self.web.miner_resume()

    async def stop_mining(self) -> bool:
        return await self.web.miner_pause()

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

    async def get_wattage_limit(self) -> int | None:
        miner_data = await self.web.info_app()
        current = miner_data.get("tune_profile")
        try:
            current_array = current.split()
            return current_array[0] if current_array[1] =="W" else None
        except:
            return None

    async def get_wattage(self) -> int | None:
        return await self.web.power()

    async def _get_hashboards(self, rpc_stats: dict | None = None) -> list[HashBoard]:
        legacy_hashboards = await super()._get_hashboards()
        temps_raw = await self.web.temp()
        if temps_raw:
            inlet_values = temps_raw.get("inlet_values", [])
            outlet_values = temps_raw.get("outlet_values", [])
            for index, hashboard in enumerate(legacy_hashboards):
                try:
                    hashboard.inlet_temp = inlet_values[index]
                    hashboard.outlet_temp = outlet_values[index]
                except:
                    continue
        return legacy_hashboards

    async def get_hashboards(self) -> list[HashBoard]:
        return await self._get_hashboards()

    async def is_overheat(self) -> bool:
        overheat = False
        try:
            overheat = await self.web.is_overheat()
        except:
            pass
        return overheat

    async def set_network(self, net_config: NetworkConfig = NetworkConfig()):
        try:
            await self.web.send_command("network_conf", **net_config.as_am_msk())
            return True
        except:
            return False

    async def get_uptime(self) -> int | None:
        uptime = await self.web.uptime()
        if uptime:
            return int(uptime)
        return uptime

    async def overheat_out(self) -> bool:
        try:
            await self.web.overheat_stop()
            return True
        except:
            return False

    async def _get_fw_ver(self, rpc_version: dict | None = None) -> str | None:
        info_app = await self.web.info_app()
        return info_app.get("bild", None)

    async def get_cloud_token(self) -> str | None:
        info_app = await self.web.info_app()
        return info_app.get("cloud_token", None)

    async def set_cloud_token(self, token: str):
        try:
            return await self.web.set_cloud_token(token)
        except Exception:
            return False