"""State storage for energy_modulator."""
# ruff: noqa: D401

#from energy_modulator.conf.energy_modulator_config import SmaEmReceiverConfig as conf
from energy_modulator.utils.async_buffers_queues import HybridDoubleBuffer
#from energy_modulator.utils.async_buffers_queues import HybridFifoQueue



class EnergyModulatorStore(HybridDoubleBuffer):
    """Application state representation for Energy Modulator Server.
    
    This will commit state changes to the listeners.
    """
    def __init__(self) -> None:
        super().__init__()