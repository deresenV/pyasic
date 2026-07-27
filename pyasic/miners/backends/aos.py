from pyasic.miners.backends import AntminerModern
from pyasic.miners.device.firmware import AosFirmware
from pyasic.web.aos import AosWebApi


class AosMiner(AosFirmware, AntminerModern):
    web: AosWebApi
    _web_cls = AosWebApi

    async def get_wattage(self) -> int | None:
        info = await self.web.get_system_info()
        return info.get("power", None)