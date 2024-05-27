"""Skyline inverter modules."""
from datetime import datetime, timedelta
import logging
import time

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.transaction import ModbusSocketFramer

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, INVERTER_POLL_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class ModbusHost:
    """Defines a Modbus endpoint."""

    def __init__(self, host: str, port: int) -> None:
        """Modbus intitialiser."""
        self.host = host
        self.port = port
        self.client = AsyncModbusTcpClient(
            self.host, self.port, framer=ModbusSocketFramer
        )

    async def read_holding_registers(self, start_address, num_registers, slave_address):
        """Read registers from an inverter."""
        if not self.client.connected:
            await self.client.connect()

        if not self.client.connected:
            return None

        try:
            return await self.client.read_holding_registers(
                start_address, num_registers, slave=slave_address
            )
        except:  # noqa: E722
            return None

    async def write_register(self, register, value, slave_address):
        """Write data back to the inverter."""
        if not self.client.connected:
            await self.client.connect()
        if not self.client.connected:
            return None

        try:
            return await self.client.write_register(
                address=register, value=value, slave=slave_address
            )
        except:  # noqa: E722
            return None


class Inverter:
    """An individual inverter."""

    def __init__(
        self,
        serial_number: str,
        model_number: str,
        slave_address: int,
        host: ModbusHost,
    ) -> None:
        """Inverter intialiser."""
        self.serial_number = serial_number
        self._slave_address = slave_address
        self.model_number = model_number
        self._host = host
        self._written_registers = {}
        self.previous_pv_energy_today = float(0)
        self.pv_energy_today_offset = float(0)
        self.master_software_version = ""
        self.slave_software_version = ""
        self.ems_software_version = ""
        self.dcdc_software_version = ""
        self.last_version_poll = None

        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.serial_number)},
            name="Skyline " + self.serial_number,
            manufacturer="Skyline",
            model=self.model_number,
        )

    def shag_pv_energy_today(self, pv_energy_today: float):
        """Shag a PV energy today from offset because CYG are useless."""
        if self.previous_pv_energy_today > pv_energy_today and pv_energy_today < 1:
            self.pv_energy_today_offset = pv_energy_today
            _LOGGER.info("Setting PV energy offset to %s", self.pv_energy_today_offset)

        self.previous_pv_energy_today = pv_energy_today
        return pv_energy_today - self.pv_energy_today_offset

    def registers_to_string(self, registers, start: int, length: int):
        """Convert a section of registers into a string."""
        data = ""
        i = 0
        while i < length:
            x = registers[start + i]
            c = (x >> 8) & 0xFF
            f = x & 0xFF

            if c > 0:
                data = data + chr(c)

            if f > 0:
                data = data + chr(f)

            i = i + 1

        return data.strip()

    async def update_software_versions(self):
        """Update software version numbers."""

        if (
            self.last_version_poll is None
            or time.time() - self.last_version_poll > 7200
        ):
            self.last_version_poll = time.time()
        else:
            return

        response = await self.read_holding_registers(0x1A1C, 3)
        self.master_software_version = self.registers_to_string(
            response.registers, 0, 3
        )

        response = await self.read_holding_registers(0x1A26, 3)
        self.slave_software_version = self.registers_to_string(response.registers, 0, 3)

        response = await self.read_holding_registers(0x1A60, 3)
        self.ems_software_version = self.registers_to_string(response.registers, 0, 3)

        response = await self.read_holding_registers(0x1A6F, 3)
        self.dcdc_software_version = self.registers_to_string(response.registers, 0, 3)

        _LOGGER.info(
            "Inverter %s versions are Master: %s, Slave: %s, EMS: %s, DCDC: %s",
            self.serial_number,
            self.master_software_version,
            self.slave_software_version,
            self.ems_software_version,
            self.dcdc_software_version,
        )

    async def write_register(self, register, value):
        """Write a register via modbus."""
        _LOGGER.info("Setting register %s to %s", register, value)
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
        """Read an array of registers through modbus."""
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
                        "Located recently written register %s", str(register_num)
                    )

                    if self._written_registers[register_num]["from"] > datetime.now():
                        _LOGGER.debug("Too new")
                    elif self._written_registers[register_num]["value"] == register:
                        _LOGGER.debug("Register value matches")
                        self._written_registers.pop(register_num, None)
                    else:
                        _LOGGER.info(
                            "Register value for %s does not match %s",
                            str(register_num),
                            str(self._written_registers[register_num]["value"]),
                        )
                        await self._host.write_register(
                            register=register_num,
                            value=self._written_registers[register_num]["value"],
                            slave_address=self._slave_address,
                        )
                        if self._written_registers[register_num]["attempts_left"] <= 1:
                            _LOGGER.info("Ran out of retries")
                            self._written_registers.pop(register_num, None)
                        else:
                            self._written_registers[register_num]["attempts_left"] = (
                                self._written_registers[register_num]["attempts_left"]
                                - 1
                            )
                            _LOGGER.info(
                                "Send retransmission with retries left of %s",
                                str(
                                    self._written_registers[register_num][
                                        "attempts_left"
                                    ]
                                ),
                            )

                register_num = register_num + 1

            return registers
        except:  # noqa: E722
            return None
