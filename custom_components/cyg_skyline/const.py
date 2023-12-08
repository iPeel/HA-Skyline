"""Constants for the CYG Skyline integration."""

from homeassistant.const import Platform
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.transaction import ModbusSocketFramer
from datetime import datetime, timedelta

DOMAIN = "cyg_skyline"
INVERTER_POLL_INTERVAL_SECONDS = 10
MODBUS_MAX_SLAVE_ADDRESS = 1  # Stops us wasting time because CYG doesn't let you change the slave address on parallel systems.
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BINARY_SENSOR,
]

MAX_FEED_IN_POWER_W = 6000

import logging

_LOGGER = logging.getLogger(__name__)


class ModbusHost:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.client = AsyncModbusTcpClient(
            self.host, self.port, framer=ModbusSocketFramer
        )

    async def read_holding_registers(self, start_address, num_registers, slave_address):
        if not self.client.connected:
            await self.client.connect()

        if not self.client.connected:
            return None

        try:
            return await self.client.read_holding_registers(
                start_address, num_registers, slave=slave_address
            )
        except:
            return None

    async def write_register(self, register, value, slave_address):
        if not self.client.connected:
            await self.client.connect()
        if not self.client.connected:
            return None

        try:
            return await self.client.write_register(
                address=register, value=value, slave=slave_address
            )
        except:
            return None


class Inverter:
    def __init__(
        self,
        serial_number: str,
        model_number: str,
        slave_address: int,
        host: ModbusHost,
    ) -> None:
        self.serial_number = serial_number
        self._slave_address = slave_address
        self.model_number = model_number
        self._host = host
        self._written_registers = {}

        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.serial_number)},
            name="CYG Inverter " + self.serial_number,
            manufacturer="CYG Sunri",
            model=self.model_number,
        )

    async def write_register(self, register, value):
        self._written_registers[register] = {
            "value": value,
            "attempts_left": 10,
            "from": datetime.now()
            + timedelta(seconds=INVERTER_POLL_INTERVAL_SECONDS - 1),
        }
        response = await self._host.write_register(
            register=register, value=value, slave_address=self._slave_address
        )
        return response

    async def read_holding_registers(self, start_address, num_registers):
        try:
            registers = await self._host.read_holding_registers(
                start_address, num_registers, slave_address=self._slave_address
            )

            if registers.isError() or len(registers.registers) == 0:
                return None

            register_num = start_address
            for register in registers.registers:
                if register_num in self._written_registers:
                    _LOGGER.debug(
                        "Located recently written register " + str(register_num)
                    )

                    if self._written_registers[register_num]["from"] > datetime.now():
                        _LOGGER.debug("Too new")
                    else:
                        if self._written_registers[register_num]["value"] == register:
                            _LOGGER.debug("Register value matches")
                            self._written_registers.pop(register_num, None)
                        else:
                            _LOGGER.info(
                                "Register value for "
                                + str(register_num)
                                + " does NOT match "
                                + str(self._written_registers[register_num]["value"])
                            )
                            await self._host.write_register(
                                register=register_num,
                                value=self._written_registers[register_num]["value"],
                                slave_address=self._slave_address,
                            )
                            if (
                                self._written_registers[register_num]["attempts_left"]
                                <= 1
                            ):
                                _LOGGER.info("Ran out of retries")
                                self._written_registers.pop(register_num, None)
                            else:
                                self._written_registers[register_num][
                                    "attempts_left"
                                ] = (
                                    self._written_registers[register_num][
                                        "attempts_left"
                                    ]
                                    - 1
                                )
                                _LOGGER.info(
                                    "Send retransmission with retries left of "
                                    + str(
                                        self._written_registers[register_num][
                                            "attempts_left"
                                        ]
                                    )
                                )

                register_num = register_num + 1

            return registers
        except:
            return None
