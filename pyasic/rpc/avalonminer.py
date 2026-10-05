# ------------------------------------------------------------------------------
#  Copyright 2025 Upstream Data Inc                                            -
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

from pyasic import settings
from pyasic.rpc.cgminer import CGMinerRPCAPI


class AvalonMinerRPCAPI(CGMinerRPCAPI):
    """An abstraction of the AvalonMiner API.

    Each method corresponds to an API command in AvalonMiner.
    """

    async def litestats(self):
        return await self.send_command("litestats")

    async def softon(self, timestamp: int) -> dict:
        """Schedule resume; some firmware versions do not acknowledge softon."""
        return await self.send_command(
            "ascset",
            parameters=f"0,softon,1:{timestamp}",
            response_timeout=settings.get("api_function_timeout", 5),
        )
