from pyasic.miners.backends.pitbit import PitBitMiner
from pyasic.miners.device.models import S19jXP, S19, S19j, S19XP, S19KPro, S19jPro, S19jProPlus


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


class PitBitMinerS19jPro(PitBitMiner, S19jPro):
    pass

class PitBitMinerS19jProPlus(PitBitMiner, S19jProPlus):
    pass