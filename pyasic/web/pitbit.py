import httpx

from pyasic import settings
from pyasic.web.antminer import AntminerModernWebAPI

class PitBitWebAPI(AntminerModernWebAPI):
    def __init__(self, ip: str):
        super().__init__(ip)
        self._api_conf = None
        self._stats = None

    async def stats(self):
        if not self._stats:
            self._stats = await self.send_command("stats")
        return self._stats

    async def miner_type(self):
        return await self.send_command("miner_type")

    async def get_api_conf(self):
        if not self._api_conf:
            url = f"http://{self.ip}:{80}/cgi/get_api_conf.cgi"
            auth = httpx.DigestAuth("root", "root")
            try:
                async with httpx.AsyncClient(transport=settings.transport()) as client:
                    data = await client.get(url, auth=auth)
                    self._api_conf = data.json()
                    return data.json()
            except httpx.HTTPError as e:
                return {"success": False, "message": f"HTTP error occurred: {str(e)}"}
        return self._api_conf

    async def _set_cloud_token(self, current_api_settings: dict):
        url = f"http://{self.ip}:{80}/cgi/set_api_conf.cgi"
        auth = httpx.DigestAuth("root", "root")
        try:
            async with httpx.AsyncClient(transport=settings.transport()) as client:
                data = await client.post(url, auth=auth, json=current_api_settings)
                return data.json()
        except httpx.HTTPError as e:
            return {"stats": False, "message": f"HTTP error occurred: {str(e)}"}

    async def set_cloud_token(self, current_api_settings: dict):
        try:
            response = await self._set_cloud_token(current_api_settings)
            return response.get("stats") == "success"
        except:
            return False
