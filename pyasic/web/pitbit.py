from pyasic.web.antminer import AntminerModernWebAPI

class PitBitWebAPI(AntminerModernWebAPI):
    pass

    def __init__(self, ip: str):
        super().__init__(ip)
        self._stats = None

    async def stats(self):
        if not self._stats:
            self._stats = await self.send_command("stats")
        return self._stats

    async def miner_type(self):
        return await self.send_command("miner_type")

    async def get_api_conf(self):
        return await self.send_command("get_api_conf")