import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN
from .inverter import Inverter

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    _LOGGER.info("Switch add entities callback")

    controller = hass.data[DOMAIN]["controller"]

    for inverter in controller.inverters:
        controller.switch_entities[
            inverter.serial_number + "_eps_enabled"
        ] = InverterSwitchEntity(
            hass,
            controller,
            inverter,
            "EPS Enabled",
            "eps_enabled",
            "mdi:power-socket",
            registerToChange=0x211C,
        )

    entities = controller.get_switch_entities()

    async_add_entities(entities)

    await controller.setup_done("switch")


class InverterSwitchEntity(SwitchEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        controller,
        inverter: Inverter,
        entityName,
        entityType,
        icon,
        category=EntityCategory.CONFIG,
        registerToChange=None,
        valueOn = 1,
        valueOff = 0
    ) -> None:
        self.currentValue = None
        self._attr_device_info = inverter.device_info
        self.inverter = inverter

        self.register_to_change = registerToChange
        self.controller = controller
        self.hass = hass
        entity_id = generate_entity_id(
            "switch.{}",
            inverter.serial_number + "_" + entityType,
            [],
            self.hass,
        )
        self.entity_id = entity_id
        self._attr_unique_id = inverter.serial_number + "_" + entityType
        self._entity_name = entityName
        self._attr_name = entityName
        self._attr_icon = icon
        self._attr_icon = icon
        self._attr_entity_registry_visible_default = False
        self.value_on = valueOn
        self.value_off = valueOff

        if category is not None:
            self._attr_entity_category = category


    def set_selected_option(self, new_value) -> None:

        if self.currentValue is not None and self.currentValue == new_value:
            # avoid noise...
            return

        _LOGGER.warning(
            "Option on "
            + self.name
            + " has been changed from "
            + str(self.currentValue)
            + " to "
            + str(new_value)
        )

        self.currentValue = new_value

        self._attr_is_on = (new_value==self.value_on)

        self._attr_current_option = new_value
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on switch."""
        self.currentValue = self.value_on
        await self.controller.set_register(
            self.inverter, self.register_to_change, self.currentValue
        )


    async def async_turn_off(self, **kwargs) -> None:
        """Turn off switch."""
        self.currentValue = self.value_off
        await self.controller.set_register(
            self.inverter, self.register_to_change, self.currentValue
        )

