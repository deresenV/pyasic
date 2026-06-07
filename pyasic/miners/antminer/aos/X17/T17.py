from pyasic.miners.backends import AosMiner
from pyasic.miners.device.models import T17, T17Plus


class AosMinerT17(AosMiner, T17):
    pass

class AosMinerT17Plus(AosMiner, T17Plus):
    pass