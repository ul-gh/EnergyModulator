"""State storage for energy_modulator."""
import asyncio

from energy_modulator.api.sma_em_protocol import EmDataDecoded
from energy_modulator.conf.energy_modulator_config import SmaEmReceiverConfig as em_receiver_config
#from energy_modulator.utils.async_buffers_queues import HybridFifoQueue



class EnergyModulatorStore():
    """Application state representation for Energy Modulator Server.
    
    This will commit state changes to the listeners.
    """
    def __init__(self) -> None:
        super().__init__()
        self.em_data: asyncio.Queue[EmDataDecoded] = asyncio.Queue(em_receiver_config.RECV_QUEUE_SIZE)


    async def get_meter_power(self) -> tuple[float, float, float, float]:
        """Return total power (power sum), power L1, power L2 and power L3."""
        # key='1:4:0', name='metering_power_absorbed', unit='W', factor=10,
        # key='2:4:0', name='metering_power_supplied', unit='W', factor=10,
        # key='21:4:0', name='metering_active_power_draw_l1', unit='W', factor=10,
        # key='22:4:0', name='metering_active_power_feed_l1', unit='W', factor=10,
        # key='41:4:0', name='metering_active_power_draw_l2', unit='W', factor=10,
        # key='41:4:0', name='metering_active_power_draw_l2', unit='W', factor=10,
        # key='61:4:0', name='metering_active_power_draw_l3', unit='W', factor=10,
        # key='62:4:0', name='metering_active_power_feed_l3', unit='W', factor=10,
        em_data = await self.em_data.get()
        measurements = em_data.measurements
        try:
            power_sum = (measurements["1:4:0"] - measurements["2:4:0"]) / 10.0
            power_l1 = (measurements["21:4:0"] - measurements["22:4:0"]) / 10.0
            power_l2 = (measurements["41:4:0"] - measurements["42:4:0"]) / 10.0
            power_l3 = (measurements["61:4:0"] - measurements["62:4:0"]) / 10.0
        except (TypeError, KeyError, ValueError):
            nan = float("nan")
            return nan, nan, nan, nan
        return power_sum, power_l1, power_l2, power_l3