"""Skyline Select Entity."""
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .inverter import Inverter

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create select entities."""

    _LOGGER.info("Select add entities callback")

    controller = hass.data[DOMAIN]["controller"]

    for inverter in controller.inverters:
        controller.select_entities[
            inverter.serial_number + "_hybrid_work_mode"
        ] = InverterSelectEntity(
            hass,
            controller,
            inverter,
            "Hybrid Work Mode",
            "hybrid_work_mode",
            "mdi:all-inclusive-box-outline",
            [
                "Self Consumption Priority",
                "Feed In Priority",
                "Time based Control",
                "Backup Supply",
                "Battery Discharge",
                "Feed In Excess Solar",
            ],
            registerToChange=0x2100,
            registerSettingsMap=[
                ["Self Consumption Priority", 0],
                ["Feed In Priority", 1],
                ["Time based Control", 2],
                ["Backup Supply", 3],
                ["Battery Discharge", 4],
                ["Feed In Excess Solar", 5],
            ],
        )

    entities = controller.get_select_entities()

    async_add_entities(entities)

    await controller.setup_done("select")


class InverterSelectEntity(SelectEntity):
    """Inverter class."""

    def __init__(
        self,
        hass: HomeAssistant,
        controller,
        inverter: Inverter,
        entityName,
        entityType,
        icon,
        optionsList,
        category=EntityCategory.CONFIG,
        unitOfMeasurement=UnitOfPower.KILO_WATT,
        deviceClass=SensorDeviceClass.POWER,
        stateClass=SensorStateClass.MEASUREMENT,
        registerToChange=None,
        registerSettingsMap=None,
    ) -> None:
        """Inverter initialiser."""

        self.currentValue = None
        self._attr_device_info = inverter.device_info
        self.inverter = inverter

        self.register_to_change = registerToChange
        self.register_settings_map = registerSettingsMap

        self._attr_options = optionsList
        self._attr_current_option = optionsList[0]
        self.controller = controller
        self.hass = hass
        entity_id = generate_entity_id(
            "select.{}",
            inverter.serial_number + "_" + entityType,
            [],
            self.hass,
        )
        self.entity_id = entity_id
        self._attr_unique_id = inverter.serial_number + "_" + entityType
        self._entity_name = entityName
        self._attr_name = entityName
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unitOfMeasurement
        self._attr_native_device_class = deviceClass
        self._attr_state_class = stateClass
        self._attr_icon = icon
        self._attr_entity_registry_visible_default = False

        if category is not None:
            self._attr_entity_category = category

    def set_selected_option(self, new_value) -> None:
        """Set the value from the inverter data."""
        value = None
        if self.register_settings_map is not None:
            for x in self.register_settings_map:
                if str(x[1]) == new_value:
                    value = x[0]
                    break
        else:
            value = str(new_value)

        if self.currentValue is not None and self.currentValue == value:
            # avoid noise...
            return

        _LOGGER.warning(
            "Option on %s has been changed from %s to %s",
            self.name,
            str(self.currentValue),
            str(value),
        )

        self.currentValue = value

        self._attr_current_option = value
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        """Receive changes from HomeAssistant and push to the inverter."""
        if self.currentValue is not None and self.currentValue == option:
            # avoid noise...
            return

        if self.register_to_change is None or self.register_to_change <= 0:
            return

        value = None

        if self.register_settings_map is not None:
            for x in self.register_settings_map:
                if str(x[0]) == option:
                    value = x[1]
                    break
        else:
            value = int(option)

        if self.register_to_change == 0x2100:
            if value == 5:
                _LOGGER.warning("Hybrid work mode is changed to match excess")
                self.controller.match_feed_in_to_excess_power = True
                value = 1
                await self.controller.update_feed_in_excess()
            else:
                self.controller.match_feed_in_to_excess_power = False

        _LOGGER.warning("Changing option on %s to %s", self.name, str(value))

        await self.controller.set_register(
            self.inverter, self.register_to_change, value
        )
