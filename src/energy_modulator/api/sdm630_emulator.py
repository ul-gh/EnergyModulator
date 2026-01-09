"""sdm630_emulator.py.

This is part of Energy Meter Gateway for Battery Inverter Feed-In Power Control.

Author: Ulrich Lukas
License: GPL v.3
"""
# FIXME: bug in device:164 "set" in parameter description, must be "info_name"
# FIXME: bug in sparse:121 Only type "list" is recognized

import asyncio
import struct

from pymodbus import ModbusDeviceIdentification
from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusServerContext,
    # ModbusSlaveContext,
    ModbusSparseDataBlock,
)
from pymodbus.framer import FramerType
from pymodbus.server import ModbusSerialServer

from energy_modulator.conf.energy_modulator_config import Sdm630EmulatorConfig as conf  # noqa: N813
from energy_modulator.store import EnergyModulatorStore, EmReadings

REG_OFFSET_L1_POWER: int = 12
# REG_OFFSET_L2_POWER: int = 14
# REG_OFFSET_L3_POWER: int = 16

# Device (Modbus slave) ID
SDM630_DEVICE_ID: int = 1


class Sdm630Emulator:
    """SDM630 Modbus meter emulator for live power control."""

    def __init__(self, store: EnergyModulatorStore) -> None:
        """Initialize Sdm630Emulator from application config."""
        # Modbus indexing scheme customarily uses zero-based offset values,
        # but register addresses per Modbus definition start at offset + 1.
        # The data structure initialized here assumes one-based register offset values.
        # This is why register offset values have to be incremented by one.
        self._data = ModbusSparseDataBlock(
            {
                # This sets 6x 2-Byte Modbus registers, for 3x phase values (4-Byte float)
                REG_OFFSET_L1_POWER + 1: (0x0000, 0x0000) * 3,
            },
            # This only means that no new register addresses can be later added.
            mutable=False,
        )
        self._data_lock = asyncio.Lock()
        self._device_context = ModbusDeviceContext(
            ir=self._data,  # Input registers
        )
        server_devices = {SDM630_DEVICE_ID: self._device_context}
        self._server_context = ModbusServerContext(devices=server_devices, single=False)
        self._identity = ModbusDeviceIdentification(
            info_name={
                "VendorName": "Ulrich Lukas",
                "ProductCode": "EnergyModulator",
                "VendorUrl": "https://github.com/ul-gh/energy_modulator/",
                "ProductName": "EnergyModulator",
                "ModelName": "Sdm630Emulator",
                "MajorMinorRevision": conf.version,
            }
        )
        self.server = ModbusSerialServer(
            context=self._server_context,  # Data storage
            identity=self._identity,  # server identify
            port=conf.modbus_port,  # serial port
            framer=FramerType.RTU,  # The framer strategy to use
            baudrate=conf.baudrate,  # The baud rate to use for the serial device
            # Deye inverters send some spurious requests which we want to ignore
            ignore_missing_devices=True,
        )
        # Hook data updating call of datastore to update this server context
        store.add_em_data_hook(self.set_power)

    async def run_forever(self) -> None:
        """Start SDM630 emulator server task."""
        await self.server.serve_forever()

    def set_power(self, readings: EmReadings) -> None:
        """Set emulated total active power by setting all phases to a third of the total power."""
        reg_vals_l1_l2_l3: list[int] = self._float_to_big_endian_reg_vals(
            readings.power_l1,
            readings.power_l2,
            readings.power_l3,
        )
        # Function code 0x04 (read input register) is mapped to the
        # respective input register setter functions by pymodbus.
        function_code: int = 0x04
        # Getting device context from server context is one option
        # context = self._server_context[SDM630_DEVICE_ID]
        # Getting device context from instance attribute is another option
        context = self._device_context
        # Using the device context setValues() function to modify data.
        # Above context store setter methods assume zero-based register offset values
        context.setValues(function_code, REG_OFFSET_L1_POWER, reg_vals_l1_l2_l3)
        # Third option is directly modifying the data block.
        # But the data block setter method assumes one-based offsets...
        # self._data.setValues(REG_OFFSET_L1_POWER + 1, l1_l2_l3_vals)

    def _float_to_big_endian_reg_vals(self, power_l1: float, power_l2: float, power_l3: float) -> list[int]:
        """Convert three phase power values to Modbus register values."""
        float32_big_endian_bytes = struct.pack(">fff", power_l1, power_l2, power_l3)
        return list(struct.unpack(">hhhhhh", float32_big_endian_bytes))
