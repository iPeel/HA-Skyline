"""Skyline communication and stats collection."""
import asyncio
import logging
import math
import struct

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    IMPORT_EXPORT_MONITOR_DURATION_SECONDS,
    IMPORT_EXPORT_THRESHOLD,
    INVERTER_POLL_INTERVAL_SECONDS,
    MODBUS_MAX_SLAVE_ADDRESS,
    NO_AGGREGATION,
    PLATFORMS,
)
from .inverter import Inverter, ModbusHost

_LOGGER = logging.getLogger(__name__)


class Controller:
    """Controller class orchestrating the data fetching and entitities."""

    def __init__(
        self, host: str, port: int, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Initialise the controller."""
        self.host = host
        self.port = port
        self.hass = hass
        self.config = entry
        self.poller_task = None
        self.have_identity_info = False

        self.sensor_entities = {}
        self.binary_sensor_entities = {}
        self.switch_entities = {}
        self.select_entities = {}
        self.number_entities = {}
        self.binary_sensor_entities = {}
        self._init_count = 0
        self.aggregates = {}
        self.inverters = []
        self.clickhouse_url = ""
        self.clickhouse_is_init = True
        self.aio_http_session = None

        _LOGGER.info("Skyline controller starting")

    def aggregate(self, name: str, value, count: int, trimTo=-1):
        """Stash a value to an aggregate array and return the average."""
        if trimTo == -1:
            trimTo = count

        if name not in self.aggregates:
            self.aggregates[name] = []

        while len(self.aggregates[name]) >= trimTo:
            self.aggregates[name].pop(0)

        self.aggregates[name].append(value)

        t = 0
        num = 0
        for v in self.aggregates[name]:
            t = t + v
            num = num + 1
            if num == count:
                break

        if NO_AGGREGATION is True:
            return value

        return t / num

    def am_exporting_importing(self, inverter: Inverter, is_import: bool) -> bool:
        """Determine if we're importing or exporting."""
        minCount = math.ceil(
            IMPORT_EXPORT_MONITOR_DURATION_SECONDS / INVERTER_POLL_INTERVAL_SECONDS
        )

        if len(self.aggregates[inverter.serial_number + "_grid_load"]) < minCount:
            return False

        vals = ""

        for v in self.aggregates[inverter.serial_number + "_grid_load"]:
            if len(vals) > 0:
                vals = vals + ","
            vals = vals + str(v)

            if is_import and v <= float(IMPORT_EXPORT_THRESHOLD):
                return False

            if not is_import and v >= float(0) - IMPORT_EXPORT_THRESHOLD:
                return False

        _LOGGER.debug(
            "Import / Export values %s so returning true with is_import as  %s",
            vals,
            str(is_import),
        )

        return True

    async def start_poller(self):
        """Start the async polling of inverter data."""

        async def periodic():
            while True:
                _LOGGER.debug("Polling Inverter Modbus")
                await asyncio.sleep(
                    INVERTER_POLL_INTERVAL_SECONDS
                )  # first because we polled it in await after init.
                await self.poll_inverters()

        task = self.config.async_create_background_task(
            self.hass, periodic(), "Skyline Inverter Poll"
        )

        self.poller_task = task

    async def poll_inverters(self):
        """Poll all inverters."""
        skyline_pv_power = float(0)
        skyline_battery_load = float(0)
        skyline_grid_load = float(0)
        skyline_grid_tied_load = float(0)
        skyline_eps_load = float(0)
        skyline_inverter_load = float(0)

        for inverter in self.inverters:
            try:
                inverter_power_data = await inverter.read_holding_registers(0x1001, 64)
                grid_power_data = await inverter.read_holding_registers(0x1300, 63)
                battery_data = await inverter.read_holding_registers(0x2000, 19)
                inverter_config_data = await inverter.read_holding_registers(0x2100, 34)
                grid_config_data = await inverter.read_holding_registers(0x30B0, 12)
                eps_data = await inverter.read_holding_registers(0x1350, 19)

                if (
                    inverter_power_data is None
                    or grid_power_data is None
                    or battery_data is None
                    or inverter_config_data is None
                    or grid_power_data.isError()
                    or battery_data.isError()
                    or inverter_config_data.isError()
                    or inverter_power_data.registers is None
                    or grid_power_data.registers is None
                    or battery_data.registers is None
                    or inverter_config_data.registers is None
                    or len(inverter_power_data.registers) < 64
                    or len(grid_power_data.registers) < 63
                    or len(battery_data.registers) < 19
                    or len(inverter_config_data.registers) < 34
                    or len(grid_config_data.registers) < 12
                    or len(eps_data.registers) < 19
                ):
                    _LOGGER.error(
                        "Skyline Inverter did not provide all results at host %s",
                        self.host,
                    )
                    return

                # if grid and battery totals are zero, smell a mis-report
                if (
                    registers_to_unsigned_32(grid_power_data.registers, 6) == 0
                    and registers_to_unsigned_32(grid_power_data.registers, 8) == 0
                    and registers_to_unsigned_32(battery_data.registers, 13) == 0
                    and registers_to_unsigned_32(battery_data.registers, 17) == 0
                ):
                    _LOGGER.error(
                        "Skyline Inverter provided too many zero registers at host %s",
                        self.host,
                    )
                    return

                self.sensor_entities[inverter.serial_number + "_soc"].set_native_value(
                    battery_data.registers[0]
                )

                inverter_pv_power = (
                    registers_to_unsigned_32(inverter_power_data.registers, 17)
                    + registers_to_unsigned_32(inverter_power_data.registers, 21)
                ) / 10000

                skyline_pv_power = skyline_pv_power + inverter_pv_power

                self.sensor_entities[
                    inverter.serial_number + "_pv_power"
                ].set_native_value(
                    round(
                        inverter_pv_power,
                        1,
                    )
                )

                self.sensor_entities[
                    inverter.serial_number + "_mppt1_power"
                ].set_native_value(
                    registers_to_unsigned_32(inverter_power_data.registers, 17) / 10000
                )

                self.sensor_entities[
                    inverter.serial_number + "_mppt2_power"
                ].set_native_value(
                    registers_to_unsigned_32(inverter_power_data.registers, 21) / 10000
                )

                inverter_battery_load = (
                    registers_to_signed_32(battery_data.registers, 9) / 10000
                )
                skyline_battery_load = skyline_battery_load + inverter_battery_load
                self.sensor_entities[
                    inverter.serial_number + "_battery_load"
                ].set_native_value(inverter_battery_load)

                inverter_grid_load = (
                    registers_to_signed_32(grid_power_data.registers, 0) / 10000
                )
                skyline_grid_load = skyline_grid_load + inverter_grid_load
                self.sensor_entities[
                    inverter.serial_number + "_grid_load"
                ].set_native_value(
                    round(
                        self.aggregate(
                            inverter.serial_number + "_grid_load",
                            inverter_grid_load,
                            math.ceil(30 / INVERTER_POLL_INTERVAL_SECONDS),
                            trimTo=math.ceil(
                                IMPORT_EXPORT_MONITOR_DURATION_SECONDS
                                / INVERTER_POLL_INTERVAL_SECONDS
                            )
                            + 1,
                        ),
                        1,
                    )
                )

                inverter_grid_tied_load = (
                    registers_to_signed_32(grid_power_data.registers, 10) / 10000
                )
                skyline_grid_tied_load = (
                    skyline_grid_tied_load + inverter_grid_tied_load
                )
                self.sensor_entities[
                    inverter.serial_number + "_grid_tied_load"
                ].set_native_value(inverter_grid_tied_load)

                inverter_eps_load = (
                    registers_to_signed_32(eps_data.registers, 3)
                    + registers_to_signed_32(eps_data.registers, 9)
                    + registers_to_signed_32(eps_data.registers, 14)
                ) / 10000

                skyline_eps_load = skyline_eps_load + inverter_eps_load
                self.sensor_entities[
                    inverter.serial_number + "_eps_load"
                ].set_native_value(inverter_eps_load)

                inverter_load = (
                    registers_to_signed_32(inverter_power_data.registers, 2)
                    + registers_to_signed_32(inverter_power_data.registers, 7)
                    + registers_to_signed_32(inverter_power_data.registers, 12)
                ) / 10000
                skyline_inverter_load = skyline_inverter_load + inverter_load
                self.sensor_entities[
                    inverter.serial_number + "_inverter_load"
                ].set_native_value(inverter_load)

                self.sensor_entities[
                    inverter.serial_number + "_pv_energy_today"
                ].set_native_value(
                    registers_to_unsigned_32(inverter_power_data.registers, 38) / 1000
                )

                self.sensor_entities[
                    inverter.serial_number + "_pv_energy_total"
                ].set_native_value(
                    registers_to_unsigned_32(inverter_power_data.registers, 32)
                )

                self.sensor_entities[
                    inverter.serial_number + "_grid_energy_in_total"
                ].set_native_value(
                    registers_to_unsigned_32(grid_power_data.registers, 6) / 100
                )

                self.sensor_entities[
                    inverter.serial_number + "_grid_energy_out_total"
                ].set_native_value(
                    registers_to_unsigned_32(grid_power_data.registers, 8) / 100
                )

                self.sensor_entities[
                    inverter.serial_number + "_grid_energy_in_today"
                ].set_native_value(
                    registers_to_unsigned_32(grid_power_data.registers, 50) / 100
                )

                self.sensor_entities[
                    inverter.serial_number + "_grid_energy_out_today"
                ].set_native_value(
                    registers_to_unsigned_32(grid_power_data.registers, 52) / 100
                )

                self.sensor_entities[
                    inverter.serial_number + "_battery_energy_in_total"
                ].set_native_value(
                    registers_to_unsigned_32(battery_data.registers, 13) / 100
                )

                self.sensor_entities[
                    inverter.serial_number + "_battery_energy_out_total"
                ].set_native_value(
                    registers_to_unsigned_32(battery_data.registers, 17) / 100
                )

                self.sensor_entities[
                    inverter.serial_number + "_battery_energy_in_today"
                ].set_native_value(
                    registers_to_unsigned_32(battery_data.registers, 11) / 100
                )

                self.sensor_entities[
                    inverter.serial_number + "_battery_energy_out_today"
                ].set_native_value(
                    registers_to_unsigned_32(battery_data.registers, 15) / 100
                )

                self.number_entities[
                    inverter.serial_number + "_battery_max_soc"
                ].set_number_value(inverter_config_data.registers[25])

                self.number_entities[
                    inverter.serial_number + "_grid_max_charge_soc"
                ].set_number_value(inverter_config_data.registers[23])

                self.number_entities[
                    inverter.serial_number + "_grid_max_charge_power"
                ].set_number_value(inverter_config_data.registers[22])

                self.number_entities[
                    inverter.serial_number + "_battery_max_charge_power"
                ].set_number_value(inverter_config_data.registers[24])

                self.number_entities[
                    inverter.serial_number + "_battery_max_power"
                ].set_number_value(inverter_config_data.registers[26])

                self.number_entities[
                    inverter.serial_number + "_grid_max_feed_in_power"
                ].set_number_value(grid_config_data.registers[10])

                self.select_entities[
                    inverter.serial_number + "_hybrid_work_mode"
                ].set_selected_option(str(inverter_config_data.registers[0]))

                self.switch_entities[
                    inverter.serial_number + "_eps_enabled"
                ].set_selected_option(inverter_config_data.registers[28])

                self.sensor_entities[
                    inverter.serial_number + "_battery_voltage"
                ].set_native_value(battery_data.registers[6] / 10)

                self.sensor_entities[
                    inverter.serial_number + "_battery_current"
                ].set_native_value(
                    registers_to_signed_32(battery_data.registers, 7) / 100
                )

                self.sensor_entities[
                    inverter.serial_number + "_grid_voltage"
                ].set_native_value(grid_power_data.registers[26] / 10)

                self.sensor_entities[
                    inverter.serial_number + "_grid_current"
                ].set_native_value(
                    registers_to_signed_32(grid_power_data.registers, 29) / 100
                )

                self.sensor_entities[
                    inverter.serial_number + "_mppt1_voltage"
                ].set_native_value(inverter_power_data.registers[15] / 10)

                self.sensor_entities[
                    inverter.serial_number + "_mppt1_current"
                ].set_native_value(inverter_power_data.registers[16] / 100)

                self.sensor_entities[
                    inverter.serial_number + "_mppt2_voltage"
                ].set_native_value(inverter_power_data.registers[19] / 10)

                self.sensor_entities[
                    inverter.serial_number + "_mppt2_current"
                ].set_native_value(inverter_power_data.registers[20] / 100)

                self.binary_sensor_entities[
                    inverter.serial_number + "_grid_am_exporting"
                ].set_binary_value(self.am_exporting_importing(inverter, False))

                self.binary_sensor_entities[
                    inverter.serial_number + "_grid_am_importing"
                ].set_binary_value(self.am_exporting_importing(inverter, True))

                self.sensor_entities[
                    inverter.serial_number + "_system_temp"
                ].set_native_value(
                    register_to_signed_16(inverter_power_data.registers[27])
                )

                # No point in the below as the inverter is always returning zero until Skyline fix it.
                # self.sensor_entities[
                #    inverter.serial_number + "_battery_temp"
                # ].set_native_value(register_to_signed_16(battery_data.registers[1]))

            except Exception as e:  # noqa: E722
                _LOGGER.info(e)
                _LOGGER.info("Error retrieving inverter stats")

        self.sensor_entities["skyline_consumer_load"].set_native_value(
            round(
                self.aggregate(
                    "skyline_consumer_load",
                    skyline_eps_load + skyline_grid_tied_load,
                    math.ceil(60 / INVERTER_POLL_INTERVAL_SECONDS),
                ),
                2,
            )
        )

        if len(self.inverters) > 1:
            self.sensor_entities["skyline_pv_power"].set_native_value(
                round(
                    self.aggregate(
                        "skyline_pv_power",
                        skyline_pv_power,
                        math.ceil(60 / INVERTER_POLL_INTERVAL_SECONDS),
                    ),
                    2,
                )
            )

            self.sensor_entities["skyline_battery_load"].set_native_value(
                round(skyline_battery_load, 2)
            )

            self.sensor_entities["skyline_grid_load"].set_native_value(
                round(skyline_grid_load, 2)
            )

            self.sensor_entities["skyline_grid_tied_load"].set_native_value(
                round(skyline_grid_tied_load, 2)
            )
            self.sensor_entities["skyline_inverter_load"].set_native_value(
                round(skyline_inverter_load, 2)
            )

            self.sensor_entities["skyline_eps_load"].set_native_value(
                round(skyline_eps_load, 2)
            )

        await self.record_stats_to_clickhouse()

    async def record_stats_to_clickhouse(self):
        """Record all our sensors to a clickhouse database if configured."""
        if self.clickhouse_url is None or len(self.clickhouse_url) < 5:
            return

        if self.clickhouse_is_init is True:
            self.aio_http_session = async_get_clientsession(self.hass)
            await self.clickhouse_exec(
                "create table if not exists skyline_stats ( at_utc DateTime ) ENGINE = MergeTree PARTITION BY toYYYYMM(at_utc) ORDER BY at_utc;"
            )

        create = ""

        columns = ""
        values = ""

        for k in self.sensor_entities:
            e: SensorEntity = self.sensor_entities[k]

            if self.clickhouse_is_init is True:
                if create == "":
                    create = (
                        create
                        + "alter table skyline_stats add column if not exists "
                        + k.replace("-", "_")
                        + " Float64"
                    )
                else:
                    create = (
                        create
                        + ", add column if not exists "
                        + k.replace("-", "_")
                        + " Float64"
                    )

            if columns == "":
                columns = k.replace("-", "_")
                values = str(e.native_value)
            else:
                columns = columns + "," + k.replace("-", "_")
                values = values + "," + str(e.native_value)

        if self.clickhouse_is_init is True:
            await self.clickhouse_exec(create + ";")
            self.clickhouse_is_init = False

        await self.clickhouse_exec(
            "insert into skyline_stats ( at_utc,"  # noqa: S608
            + columns
            + ") values ( toDateTime(now(), 'UTC'),"
            + values
            + ");"
        )

    async def clickhouse_exec(self, cmd: str):
        """Execute a statement to the clikchouse database."""
        try:
            x = await self.aio_http_session.post(self.clickhouse_url, data=cmd)

            if x.status != 200:
                _LOGGER.error("Clickhouse command failed: %s", cmd)
        except:  # noqa: E722
            _LOGGER.error("Clickhouse command failed: %s", cmd)

    async def set_register(self, inverter: Inverter, register: int, value: int):
        """Set a modbus register from a change in HA."""
        try:
            await inverter.write_register(register, value)
        except:  # noqa: E722
            _LOGGER.info("Pymodbus still raising errors on register writes")
        await self.poll_inverters()

    async def update_ha_state(self):
        """Schedule an update for all other included entities."""

    async def get_identity_info(self):
        """Obtain the serial number, model etc."""
        hosts = self.host.replace(" ", "").split(sep=",")
        for host in hosts:
            _LOGGER.info("Scanning for slaves on modbus host %s", host)
            port = self.port
            if ":" in host:
                port = int(host.split(sep=":")[1])
                host = host.split(sep=":")[0]

            modbus = ModbusHost(host=host, port=port)
            detect_loops = 5  # We want to detect at least one slave on each specified modbus adapter, so retry if we don't

            while detect_loops > 0:
                detect_loops = detect_loops - 1
                for slave in range(1, MODBUS_MAX_SLAVE_ADDRESS + 1):
                    try:
                        _LOGGER.info("Attempting to query slave %s", str(slave))
                        modelResponse = await modbus.read_holding_registers(
                            0x1A00, 8, slave_address=slave
                        )

                        _LOGGER.info("Query complete, querying serial")

                        if modelResponse.isError():
                            _LOGGER.info(
                                "Stopped scanning for modbus slaves at slave %s",
                                str(slave),
                            )
                            break

                        serialResponse = await modbus.read_holding_registers(
                            0x1A10, 8, slave_address=slave
                        )

                        _LOGGER.info("Query complete")

                        inverter = Inverter(
                            serial_number=registers_to_string(
                                serialResponse.registers, 0, 8
                            ),
                            model_number=registers_to_string(
                                modelResponse.registers, 0, 8
                            ),
                            slave_address=slave,
                            host=modbus,
                        )

                        _LOGGER.info("Created inverter")

                        _LOGGER.info(
                            "Skyline Model Number is %s", inverter.model_number
                        )
                        _LOGGER.info(
                            "Skyline Serial Number is %s", inverter.serial_number
                        )
                        detect_loops = 0
                        self.inverters.append(inverter)
                        self.have_identity_info = True
                    except:  # noqa: E722
                        _LOGGER.info(
                            "Stopped scanning with exception for modbus host %s at slave %s",
                            host,
                            str(slave),
                        )
                        if detect_loops <= 0:
                            break

    def __del__(self):
        """Log deletion."""
        _LOGGER.debug("Controller deleted")
        self.terminate()

    def terminate(self):
        """End the controller."""
        if self.poller_task is not None:
            self.poller_task.cancel()
            self.poller_task = None
            _LOGGER.info("Skyline is no longer polling")

    async def initialise(self):
        """Self intialisation."""
        await self.get_identity_info()

    def get_sensor_entities(self):
        """Get sensor entities."""

        return list(self.sensor_entities.values())

    def get_switch_entities(self):
        """Get switch entities."""

        return list(self.switch_entities.values())

    def get_select_entities(self):
        """Get select entities."""

        return list(self.select_entities.values())

    def get_number_entities(self):
        """Get number entities."""

        return list(self.number_entities.values())

    def get_binary_sensor_entities(self):
        """Get binary sensor entities."""

        return list(self.binary_sensor_entities.values())

    async def setup_done(self, name):
        """Entities setup is done."""
        self._init_count = self._init_count + 1
        _LOGGER.debug("Entities %s setup done", name)
        if self._init_count >= len(PLATFORMS):
            await self.poll_inverters()
            await self.start_poller()


def registers_to_string(registers, start: int, length: int):
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


def registers_to_signed_32(registers, pos):
    """Convert a section of registers into a signed 32."""
    regs = [registers[pos], registers[pos + 1]]
    b = struct.pack(">2H", *regs)
    return struct.unpack(">l", b)[0]


def register_to_signed_16(register):
    """Convert a section of registers into a signed 16."""
    b = struct.pack(">H", register)
    return struct.unpack(">h", b)[0]


def registers_to_unsigned_32(registers, pos):
    """Convert a section of registers into a unsigned 32."""
    regs = [registers[pos], registers[pos + 1]]
    b = struct.pack(">2H", *regs)
    return struct.unpack(">L", b)[0]
