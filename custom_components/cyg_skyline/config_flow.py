"""Config flow for CYG Skyline integration."""
from __future__ import annotations

import logging
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host", default="192.168.1.254", description="Host(s)"): str,
        vol.Required("port", default=502, description="Port"): int,
    }
)


class ModbusHub:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self, host: str, port: int) -> None:
        """Initialize."""

        self.hosts = host.replace(" ", "").split(sep=",")
        self.port = port

    async def checkHost(self, host, port) -> bool:
        """Test we can access the configured host."""
        try:
            client = AsyncModbusTcpClient(host=host, port=port)
            await client.connect()
            if not client or not client.connected:
                _LOGGER.error("CYG Modbus host invalid")
                return False

            response = await client.read_holding_registers(address=0x1A10, count=8, slave=1)
            if not response:
                _LOGGER.error("CYG Modbus no response from host")
                return False

            serial = ""
            for x in response.registers:
                c = (x >> 8) & 0xFF
                f = x & 0xFF

                serial = serial + chr(c) + chr(f)

            _LOGGER.info("Connected to inverter serial number %s", serial)
        except:  # noqa: E722
            return False

        return True

    async def authenticate(self) -> bool:
        """Test if we can communicate with the host."""

        for host in self.hosts:
            _LOGGER.info("Scanning for slaves on modbus host %s", host)
            port = self.port
            if ":" in host:
                port = int(host.split(sep=":")[1])
                host = host.split(sep=":")[0]

            if await self.checkHost(host, port) is False:
                return False

        return True


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    hub = ModbusHub(data["host"], data["port"])

    if not await hub.authenticate():
        raise CannotConnect

    # Return info that you want to store in the config entry.
    return {"title": "Modbus TCP-RTU on " + data["host"]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CYG Skyline."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        entries = self.hass.config_entries.async_entries(DOMAIN)
        if entries:
            return self.async_abort(reason="already_setup")

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    def async_get_options_flow(
        config_entry: ConfigEntry,  # noqa: N805
    ) -> OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class OptionsFlowHandler(OptionsFlow):
    """Skyline Options Flow handler."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Skyline Options Flow handler intiialiser."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # self.config_entry.version = 1
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=user_input,
                    options=self.config_entry.options,
                    title="Modbus TCP-RTU on " + user_input["host"],
                )
                return self.async_create_entry(
                    title="Modbus TCP-RTU on " + user_input["host"],
                    data=user_input,
                )

        clickhouse_url = ""
        if "clickhouse_url" in self.config_entry.data:
            clickhouse_url = self.config_entry.data["clickhouse_url"]

        excess_rate_soc = 3
        if "excess_rate_soc" in self.config_entry.data:
            excess_rate_soc = self.config_entry.data["excess_rate_soc"]

        excess_min_feed_in_rate = 0
        if "excess_min_feed_in_rate" in self.config_entry.data:
            excess_min_feed_in_rate = self.config_entry.data["excess_min_feed_in_rate"]

        excess_max_soc_deviation_w = 3000
        if "excess_max_soc_deviation_w" in self.config_entry.data:
            excess_max_soc_deviation_w = self.config_entry.data[
                "excess_max_soc_deviation_w"
            ]
        excess_load_entity_id = ""
        if "excess_load_entity_id" in self.config_entry.data:
            excess_load_entity_id = self.config_entry.data["excess_load_entity_id"]

        excess_load_percentage = 100
        if "excess_load_percentage" in self.config_entry.data:
            excess_load_percentage = self.config_entry.data["excess_load_percentage"]
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("host", default=self.config_entry.data["host"]): str,
                    vol.Required("port", default=self.config_entry.data["port"]): int,
                    vol.Optional("clickhouse_url", default=clickhouse_url): str,
                    vol.Optional("excess_rate_soc", default=excess_rate_soc): int,
                    vol.Optional(
                        "excess_load_percentage", default=excess_load_percentage
                    ): int,
                    vol.Optional(
                        "excess_min_feed_in_rate", default=excess_min_feed_in_rate
                    ): int,
                    vol.Optional(
                        "excess_max_soc_deviation_w", default=excess_max_soc_deviation_w
                    ): int,
                    vol.Optional(
                        "excess_load_entity_id", default=excess_load_entity_id
                    ): str,
                }
            ),
            errors=errors,
        )
