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
from __future__ import annotations

import httpx

from pyasic import settings
from pyasic.web.antminer import AntminerModernWebAPI


class PitBitWebAPI(AntminerModernWebAPI):
    """Web API client for PitBit firmware miners."""

    async def miner_type(self) -> dict:
        """Retrieve the miner type information.

        Returns:
            dict: A dictionary containing the miner type details.
        """
        return await self.send_command("miner_type")

    async def get_api_conf(self) -> dict:
        """Retrieve the API configuration from the miner.

        Returns:
            dict: A dictionary containing the API configuration.
        """
        return await self.send_command("get_api_conf")

    async def log(self) -> str | dict:
        """Retrieve the miner log as plain text.

        Returns:
            str: The raw log text, or a dict with error info on failure.
        """
        url = f"http://{self.ip}:{self.port}/cgi-bin/log.cgi"
        auth = httpx.DigestAuth(self.username, self.pwd)
        try:
            async with httpx.AsyncClient(transport=settings.transport()) as client:
                data = await client.get(url, auth=auth)
                return data.text
        except httpx.HTTPError as e:
            return {"success": False, "message": f"HTTP error occurred: {str(e)}"}
