"""The Skyline integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .controller import Controller

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Skyline from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
        hass.data[DOMAIN]["entities"] = []
    _LOGGER.info("*** STARTUP***")

    controller = Controller(entry.data["host"], entry.data["port"], hass, entry)

    if "clickhouse_url" in entry.data:
        controller.clickhouse_url = entry.data["clickhouse_url"]

    hass.data[DOMAIN]["controller"] = controller
    await controller.initialise()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


def setup(hass: HomeAssistant, entry: ConfigEntry):
    """Set up is called when Home Assistant is loading our component."""

    def handle_set_setpoint(call):
        controller = hass.data[DOMAIN]["controller"]

        if "target_soc_percent" in call.data:
            controller.excess_target_soc = call.data["target_soc_percent"]

        if "target_soc_rate" in call.data:
            controller.excess_rate_soc = float(call.data["target_soc_rate"]) / 10

        if "min_feed_in_rate" in call.data:
            controller.excess_min_feed_in_rate = int(call.data["min_feed_in_rate"])

        if "rapid_change_threshold" in call.data:
            controller.excess_rapid_change_threshold = int(
                call.data["rapid_change_threshold"]
            )

        if "slow_change_threshold" in call.data:
            controller.excess_slow_change_threshold = int(
                call.data["slow_change_threshold"]
            )

        if "slow_change_period_seconds" in call.data:
            controller.excess_slow_change_period_seconds = int(
                call.data["slow_change_period_seconds"]
            )

        if "averaging_period_seconds" in call.data:
            controller.excess_averaging_period_seconds = int(
                call.data["averaging_period_seconds"]
            )

        if "max_soc_deviation_w" in call.data:
            controller.excess_max_soc_deviation_kw = (
                float(call.data["max_soc_deviation_w"]) / 1000
            )

        if ("excess_load_percentage") in call.data:
            controller.self.excess_load_ratio = (
                float(call.data["excess_load_percentage"]) / 100
            )

    hass.services.register(DOMAIN, "set_excess_params", handle_set_setpoint)

    _LOGGER.info("Registered Inverter services")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    if hass.data[DOMAIN]["controller"] is not None:
        hass.data[DOMAIN]["controller"].terminate()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", entry.version)

    return True
