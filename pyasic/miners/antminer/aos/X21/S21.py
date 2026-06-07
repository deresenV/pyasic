from pyasic.miners.backends import AosMiner
from pyasic.miners.device.models import S21, S21Plus, S21Pro, S21XP, S21Hydro, S21PlusHydro


class AosMinerS21(AosMiner, S21):
    pass

class AosMinerS21Plus(AosMiner, S21Plus):
    pass

class AosMinerS21Pro(AosMiner, S21Pro):
    pass

class AosMinerS21XP(AosMiner, S21XP):
    pass

class AosMinerS21Hydro(AosMiner, S21Hydro):
    pass

class AosMinerS21PlusHydro(AosMiner, S21PlusHydro):
    pass