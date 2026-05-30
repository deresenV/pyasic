from pyasic.miners.backends import BMMiner
from pyasic.miners.device.firmware import AosFirmware
from pyasic.web.aos import AosWebApi


class AosMiner(AosFirmware, BMMiner):
    web: AosWebApi
    _web_cls = AosWebApi

    async def get_wattage(self) -> int | None:
        info = await self.web.get_system_info()
        return info.get("power", None)