import httpx

from pyasic import settings
from pyasic.misc.response_cache import cached_response
from pyasic.web.antminer import AntminerModernWebAPI

class PitBitWebAPI(AntminerModernWebAPI):
    def __init__(self, ip: str):
        super().__init__(ip)
        self._api_conf = None
        self._stats = None

    async def stats(self):
        return await cached_response(
            self, "_stats", "web_response_cache_enabled",
            lambda: self.send_command("stats"),
        )

    async def miner_type(self):
        return await self.send_command("miner_type")

    async def get_api_conf(self):
        async def fetch_api_conf():
            url = f"http://{self.ip}:{80}/cgi/get_api_conf.cgi"
            auth = httpx.DigestAuth("root", "root")
            try:
                async with httpx.AsyncClient(transport=settings.transport()) as client:
                    data = await client.get(url, auth=auth)
                    if data.status_code == 200:
                        return data.json()
                    return {"success": False, "message": f"HTTP {data.status_code}"}
            except httpx.HTTPError as e:
                return {"success": False, "message": f"HTTP error occurred: {str(e)}"}

        return await cached_response(
            self, "_api_conf", "web_response_cache_enabled", fetch_api_conf
        )

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
