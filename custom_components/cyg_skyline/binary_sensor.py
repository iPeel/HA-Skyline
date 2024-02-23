import logging
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.number import NumberEntity
from .const import DOMAIN, Inverter

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    _LOGGER.info("Number add entities callback")

    controller = hass.data[DOMAIN]["controller"]

    for inverter in controller.inverters:
        controller.binary_sensor_entities[
            inverter.serial_number + "_grid_am_exporting"
        ] = InverterBinarySensorEntity(
            hass,
            controller,
            inverter,
            "Am Exporting",
            "grid_am_exporting",
            "mdi:transmission-tower-import",
            deviceClass=BinarySensorDeviceClass.POWER,
        )

        controller.binary_sensor_entities[
            inverter.serial_number + "_grid_am_importing"
        ] = InverterBinarySensorEntity(
            hass,
            controller,
            inverter,
            "Am Importing",
            "grid_am_importing",
            "mdi:transmission-tower-export",
            deviceClass=BinarySensorDeviceClass.POWER,
        )

    entities = controller.get_binary_sensor_entities()

    async_add_entities(entities)

    await controller.setup_done("binary_sensor")


class InverterBinarySensorEntity(BinarySensorEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        controller,
        inverter: Inverter,
        entityName,
        entityType,
        icon,
        category=None,
        deviceClass=None,
    ) -> None:
        self.currentValue = None
        self._attr_device_info = inverter.device_info
        self.inverter = inverter
        self.controller = controller
        self.hass = hass
        entity_id = generate_entity_id(
            "sensor.{}",
            inverter.serial_number + "_" + entityType,
            [],
            self.hass,
        )
        self.entity_id = entity_id
        self._attr_unique_id = inverter.serial_number + "_" + entityType
        self._entity_name = entityName
        self._attr_name = entityName
        self._attr_icon = icon

        if deviceClass is not None:
            self._attr_device_class = deviceClass

        self._attr_is_on = False
        self.currentValue = False

        if category is not None:
            self._attr_entity_category = category

    def set_binary_value(self, new_state: bool) -> None:
        newValue = new_state

        if self.currentValue is not None and self.currentValue == newValue:
            # avoid noise...
            return

        self._attr_is_on = newValue
        self.currentValue = newValue

        self._async_write_ha_state()
