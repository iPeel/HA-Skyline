"""Constants for the Skyline integration."""

from homeassistant.const import Platform

DOMAIN = "cyg_skyline"
INVERTER_POLL_INTERVAL_SECONDS = 10
IMPORT_EXPORT_MONITOR_DURATION_SECONDS = 120
IMPORT_EXPORT_THRESHOLD = 0.1
MODBUS_MAX_SLAVE_ADDRESS = 1  # Stops us wasting time because Skyline doesn't let you change the slave address on parallel systems.
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

MAX_FEED_IN_POWER_W = 6000
MAX_GRID_EXPORT_POWER_W = 6000
NO_AGGREGATION = True
