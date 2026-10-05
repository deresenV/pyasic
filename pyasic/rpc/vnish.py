from pyasic.misc.response_cache import cached_response
from pyasic.rpc.bmminer import BMMinerRPCAPI


class VNishRPCAPI(BMMinerRPCAPI):
    """BMMiner RPC commands with instance-scoped Vnish stats caching."""

    def __init__(self, ip: str, port: int = 4028, api_ver: str = "0.0.0"):
        super().__init__(ip, port, api_ver)
        self._stats = None

    async def stats(self) -> dict:
        return await cached_response(
            self, "_stats", "rpc_response_cache_enabled", super().stats
        )
