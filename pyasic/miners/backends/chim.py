from pyasic.miners.backends import AntminerModern
from pyasic.miners.device.firmware import ChimFirmware


class ChimMining(ChimFirmware, AntminerModern):

    async def stop_mining(self) -> bool:
        result = await self.stop_mining()
        await self.reboot() # need reboot for claim suspend mode
        return result