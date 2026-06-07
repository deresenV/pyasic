from pyasic.miners.backends import AosMiner
from pyasic.miners.device.models import S17, S17Pro, S17Plus


class AosMinerS17(AosMiner, S17):
    pass

class AosMinerS17Pro(AosMiner, S17Pro):
    pass

class AosMinerS17Plus(AosMiner, S17Plus):
    pass