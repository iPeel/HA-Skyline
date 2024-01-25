"""The Skyline integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS

import logging
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
    hass.data[DOMAIN]["controller"] = controller
    await controller.initialise()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

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
