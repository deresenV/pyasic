from enum import Enum
from typing import Optional

from pydantic import BaseModel

class NetType(str, Enum):
    static = "Static"
    dynamic = "DHCP"

    def as_am_msk(self):
        return {
            "nettype": self.value
        }

    def as_am_modern(self):
        if self.value == NetType.static.value:
            return {
                "ipPro": 1
            }
        elif self.value == NetType.dynamic.value:
            return {
                "ipPro": 1
            }

class HostName(str, Enum):
    antminer = "Antminer"


    def as_am_msk(self):
        return {
            "hostname": self.value
        }

    def as_am_modern(self):
        return {
            "ipHost": self.value
        }

class NetworkConfig(BaseModel):
    ip: str = ""
    dns: str = ""
    gateway: str = ""
    host_name: HostName = HostName.antminer
    nettype: NetType = NetType.dynamic
    net_mask: str = ""

    def as_dict(self) -> dict:
        """Converts the NetworkConfig object to a dictionary."""
        return self.model_dump()

    def as_am_msk(self):
        return {
            "dns_servers": self.dns,
            "gateway": self.gateway,
            **self.host_name.as_am_msk(),
            "ip_address": self.ip,
            "netmask": self.net_mask,
            **self.nettype.as_am_msk()
        }

    def as_am_modern_dhcp(self):
        return {
            **self.host_name.as_am_modern(),
            **self.nettype.as_am_modern(),
            "ipAddress": self.ip,
            "ipSub": self.net_mask,
            "ipGateway": self.gateway,
            "ipDns": self.dns
        }
