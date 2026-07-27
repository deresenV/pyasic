from pyasic.miners.backends import AntminerModern
from pyasic.miners.device.firmware import ChimFirmware


class ChimMining(ChimFirmware, AntminerModern):
    pass