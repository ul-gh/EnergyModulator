"""Energy Modulator MQTT API for remote control and telemetry."""

import aiomqtt
import logging

from energy_modulator.conf.energy_modulator_config import MqttConfig as conf
from energy_modulator.store import EnergyModulatorStore

logger = logging.getLogger(__name__)

# Does this test the connection?
MQTT_TIMEOUT: float = 5.0


class MqttApi:
    def __init__(self, store: EnergyModulatorStore) -> None:
        self._store = store
        self._client = aiomqtt.Client(
            conf.BROKER,
            conf.PORT,
            clean_session=True,
            timeout=MQTT_TIMEOUT,
        )

    async def run_forever(self) -> None:
        await self._client.subscribe(conf.TOPIC_POWER_CONTROL)
        async for msg in self._client.messages:
            p_offset = float(msg.payload)
            await self._store.set_p_offset(p_offset)
