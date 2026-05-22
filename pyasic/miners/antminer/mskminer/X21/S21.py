from pyasic.miners.backends import MSKMiner
from pyasic.miners.device.models import S21, S21Pro, S21XP, S21Plus


class MSKMinerS21(MSKMiner, S21):
    pass

class MSKMinerS21Pro(MSKMiner, S21Pro):
    pass

class MSKMinerS21XP(MSKMiner, S21XP):
    pass

class MSKMinerS21Plus(MSKMiner, S21Plus):
    pass