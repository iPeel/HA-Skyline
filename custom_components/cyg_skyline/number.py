"""CYG Skyline Number Entities."""
import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MAX_FEED_IN_POWER_W
from .inverter import Inverter

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up entities on intialisation."""
    _LOGGER.info("Number add entities callback")

    controller = hass.data[DOMAIN]["controller"]

    for inverter in controller.inverters:
        controller.number_entities[
            inverter.serial_number + "_battery_max_power"
        ] = InverterNumberEntity(
            hass,
            controller,
            inverter,
            "Battery Discharge Max Power",
            "battery_max_power",
            "mdi:home-battery-outline",
            registerToChange=0x211A,
            minValue=0,
            maxValue=6,
            stepSize=0.5,
            valueMultiplier=1000,
            adjustForParallel=True,
        )

        controller.number_entities[
            inverter.serial_number + "_grid_max_charge_power"
        ] = InverterNumberEntity(
            hass,
            controller,
            inverter,
            "Grid Charge Max Power",
            "grid_max_charge_power",
            "mdi:transmission-tower-export",
            registerToChange=0x2116,
            minValue=0,
            maxValue=6,
            stepSize=0.5,
            valueMultiplier=1000,
            adjustForParallel=True,
        )

        controller.number_entities[
            inverter.serial_number + "_battery_max_charge_power"
        ] = InverterNumberEntity(
            hass,
            controller,
            inverter,
            "Battery Max Charge Power",
            "battery_max_charge_power",
            "mdi:battery-positive",
            registerToChange=0x2118,
            minValue=0,
            maxValue=6,
            stepSize=0.1,
            valueMultiplier=1000,
            adjustForParallel=True,
        )

        controller.number_entities[
            inverter.serial_number + "_grid_max_feed_in_power"
        ] = InverterNumberEntity(
            hass,
            controller,
            inverter,
            "Grid Feed In Max Power",
            "grid_max_feed_in_power",
            "mdi:transmission-tower-import",
            registerToChange=0x30BA,
            minValue=0,
            maxValue=MAX_FEED_IN_POWER_W / 1000,
            stepSize=0.1,
            valueMultiplier=1000,
            adjustForParallel=True,
        )

        controller.number_entities[
            inverter.serial_number + "_grid_max_charge_soc"
        ] = InverterNumberEntity(
            hass,
            controller,
            inverter,
            "Grid Charge End SoC",
            "grid_max_charge_soc",
            "mdi:battery-charging-high",
            registerToChange=0x2117,
            minValue=0,
            maxValue=100,
            stepSize=5,
            valueMultiplier=1,
            unitOfMeasurement=PERCENTAGE,
            deviceClass=SensorDeviceClass.BATTERY,
            stateClass=SensorStateClass.MEASUREMENT,
        )

        controller.number_entities[
            inverter.serial_number + "_battery_max_soc"
        ] = InverterNumberEntity(
            hass,
            controller,
            inverter,
            "Battery Max SoC",
            "battery_max_soc",
            "mdi:battery-arrow-up",
            registerToChange=0x2119,
            minValue=0,
            maxValue=100,
            stepSize=5,
            valueMultiplier=1,
            unitOfMeasurement=PERCENTAGE,
            deviceClass=SensorDeviceClass.BATTERY,
            stateClass=SensorStateClass.MEASUREMENT,
        )

        controller.number_entities[
            inverter.serial_number + "_excess_target_soc"
        ] = InverterNumberEntity(
            hass,
            controller,
            inverter,
            "Excess Target SoC",
            "excess_target_soc",
            "mdi:function-variant",
            registerToChange=None,
            function_on_change=controller.set_excess_target_soc,
            minValue=0,
            maxValue=100,
            stepSize=5,
            valueMultiplier=1,
            unitOfMeasurement=PERCENTAGE,
            category=EntityCategory.CONFIG
        )

    entities = controller.get_number_entities()

    async_add_entities(entities)

    await controller.setup_done("number")


class InverterNumberEntity(NumberEntity):
    """Number entity for inverters."""

    def __init__(
        self,
        hass: HomeAssistant,
        controller,
        inverter: Inverter,
        entityName,
        entityType,
        icon,
        unitOfMeasurement=UnitOfPower.KILO_WATT,
        deviceClass=SensorDeviceClass.POWER,
        stateClass=SensorStateClass.MEASUREMENT,
        minValue=0,
        maxValue=0,
        stepSize=1,
        category=None,
        registerToChange=None,
        valueMultiplier=1,
        adjustForParallel=False,
        function_on_change=None,
    ) -> None:
        """Initialise a number entity."""
        self.currentValue = None
        self.inverter = inverter
        self._attr_device_info = inverter.device_info

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
        self._attr_native_unit_of_measurement = unitOfMeasurement
        self._attr_native_device_class = deviceClass
        self._attr_state_class = stateClass
        self._attr_icon = icon
        self._attr_mode = NumberMode.BOX
        self.function_on_change = function_on_change

        if category is not None:
            self._attr_entity_category = category

        self._attr_native_min_value = minValue

        if adjustForParallel is True:
            self._attr_native_max_value = maxValue * len(self.controller.inverters)
            _LOGGER.info(
                "Setting maximum value to %s",
                str(maxValue * len(self.controller.inverters)),
            )
        else:
            self._attr_native_max_value = maxValue

        self._attr_native_step = stepSize

        self.register_to_change = registerToChange
        self.value_multiplier = valueMultiplier

        self._attr_entity_registry_visible_default = False
        self.adjust_for_parallel = adjustForParallel

    def set_native_value(self, value: float) -> None:
        """Set the native value."""
        _LOGGER.info("Set Native Value")

    async def async_set_native_value(self, value: float) -> None:
        """Set the value from a HA interaction."""
        _LOGGER.info("Set Async Value")
        if self.currentValue is not None and self.currentValue == value:
            # avoid noise...
            return

        if self.function_on_change is not None:
            await self.function_on_change(value)

        if self.register_to_change is not None:
            # self.currentValue = value LEAVE THIS UNCHANGED, let the next poller confirm the change instead.
            await self.controller.set_register(
                self.inverter,
                self.register_to_change,
                int(value * self.get_value_multiplier()),
            )

    def get_value_multiplier(self) -> float:
        """Get the amount to m,ultiply the value from based on how many parallel inverters there are."""
        if self.adjust_for_parallel is True and len(self.controller.inverters) > 1:
            return self.value_multiplier / len(self.controller.inverters)

        return self.value_multiplier

    def set_number_value(self, new_state: float) -> None:
        """Set the HA value from the inverter's modbus response."""
        newValue = new_state / self.get_value_multiplier()

        if self.currentValue is not None and self.currentValue == newValue:
            # avoid noise...
            return

        self.currentValue = newValue

        self._attr_native_value = self.currentValue
        self.async_write_ha_state()
