from pyasic.miners.backends import AosMiner
from pyasic.miners.device.models import S19, S19Pro, S19i, S19Plus, S19ProPlus, S19XP, S19a, S19aPro, S19KPro, \
    S19ProPlusHydro, S19Hydro, S19ProHydro, S19L, S19jPlus, S19jPro, S19jNoPIC, S19j, S19jXP, S19jProPlus


class AosMinerS19(AosMiner, S19):
    pass

class AosMinerS19Pro(AosMiner, S19Pro):
    pass

class AosMinerS19i(AosMiner, S19i):
    pass

class AosMinerS19Plus(AosMiner, S19Plus):
    pass

class BMMinerS19Pro(AosMiner, S19Pro):
    pass


class AosMinerS19ProPlus(AosMiner, S19ProPlus):
    pass


class AosMinerS19XP(AosMiner, S19XP):
    pass


class AosMinerS19a(AosMiner, S19a):
    pass


class AosMinerS19aPro(AosMiner, S19aPro):
    pass


class AosMinerS19j(AosMiner, S19j):
    pass


class AosMinerS19jNoPIC(AosMiner, S19jNoPIC):
    pass


class AosMinerS19jPro(AosMiner, S19jPro):
    pass


class AosMinerS19jPlus(AosMiner, S19jPlus):
    pass


class AosMinerS19L(AosMiner, S19L):
    pass


class AosMinerS19ProHydro(AosMiner, S19ProHydro):
    pass


class AosMinerS19Hydro(AosMiner, S19Hydro):
    pass


class AosMinerS19ProPlusHydro(AosMiner, S19ProPlusHydro):
    pass


class AosMinerS19KPro(AosMiner, S19KPro):
    pass


class AosMinerS19jXP(AosMiner, S19jXP):
    pass


class AosMinerS19jProPlus(AosMiner, S19jProPlus):
    pass
