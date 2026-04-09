from pyasic.device.algorithm import AlgoHashRateType
from pyasic.miners.backends.antminer import AntminerModernWebAPI
from pyasic.miners.backends.pitbit import PitBitMiner
from pyasic.miners.device.models import S19jXP, S19, S19j, S19XP, S19KPro


class PitBitMinerS19(PitBitMiner, S19):
    pass

class PitBitMinerS19JXP(PitBitMiner, S19jXP):
    pass


class PitBitMinerS19J(PitBitMiner, S19j):
    pass

class PitBitMinerS19XP(PitBitMiner, S19XP):
    pass

class PitBitMinerS19KPro(PitBitMiner, S19KPro):
    pass