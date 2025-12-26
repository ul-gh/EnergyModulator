"""State storage for energy_modulator."""
# ruff: noqa: D401
from typing import cast

from include.sma_em.speedwiredecoder import decode_speedwire # type: ignore
#from energy_modulator.conf.energy_modulator_config import SmaEmReceiverConfig as conf
from energy_modulator.utils.async_buffers_queues import HybridDoubleBuffer
#from energy_modulator.utils.async_buffers_queues import HybridFifoQueue



class EnergyModulatorStore(HybridDoubleBuffer):
    """Application state representation for Energy Modulator Server.
    
    This will commit state changes to the listeners.
    """
    def __init__(self) -> None:
        super().__init__()


    async def get_power(self) -> tuple[float, float, float, float]:
        """Return total power (power sum), power L1, power L2 and power L3."""
        emparts = cast("dict[str, float]", await self.get_readings())
        power_l1 = emparts["p1consume"] - emparts["p1supply"]
        power_l2 = emparts["p2consume"] - emparts["p2supply"]
        power_l3 = emparts["p3consume"] - emparts["p3supply"]
        power_sum = power_l1 + power_l2 + power_l3
        return power_sum, power_l1, power_l2, power_l3


    async def get_readings(self) -> dict[str, float|int|str]:
        """Get meter read-out values, returned as a dict."""
        bytes_in = await self.get()
        return cast("dict[str, float|int|str]", decode_speedwire(bytes_in))