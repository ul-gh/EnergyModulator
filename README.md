# EnergyModulator
## This is a work-in-progress repository: DO NOT USE!

Energy Metering Gateway Application for Grid-Coupled Inverter Power Control.

EnergyModulator runs as a user-mode system service on Linux devices.

This enables low-latency control of grid-side or load-side instantaneous
influx and outgoing power for battery, solar or hybrid inverters.

Possible application setup is inverter hardware evaluation with respect to
dynamic feed-in tariffs, direct energy trading or load-shaping using a
supervisory plant controller or energy management system (EMS).

EnergyModulator is intended for an expert audience for use in development,
performance testing or evaluation purpuses. Use at your own risk!

## Description
This application acts as a gateway between metering devices, power inverters and
supervisory control over MQTT and local logging.

Metering devices and inverters can be attached using Modbus TCP (Ethernet),
Modbus RTU (RS485), serial line, CAN bus etc.

Protcols implemented are SMA Energy Metering Protocol (Sunny Home Manager 2.0 or Emeter-20),
Eastron SDM630 (Deye).

Working principle is superposition of an arbitrary power offset (positive or negative)
to the values reported from the meter.

These values are forwarded via UDP Broadcast/Multicast or Modbus request
or provided on the respective protocol endpoints as soon as available or with
configurable rate-limit.

This mode 100% keeps the original dynamics and tuning settings of the closed-loop controller
implemented in the inverter, notably that of the zero-export power controller.

This application uses the Python asyncio framework for asynchronous programming,
establishing low-latency cooperative multi-tasking.

The grid-side or inverter-side instantaneous power setpoint can be set and
continuously updated using the configured MQTT topic.

MQTT default topic: cmd/energy_modulator/set_power_offset

EnergyModulator is configured by editing src/energy_modulator/conf/energy_modulator_config.py.


2025-12-26 Ulrich Lukas