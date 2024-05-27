"""Skyline diagnostics sensors."""
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .inverter import Inverter

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensor platform."""

    _LOGGER.info("Skyline async_setup_entry setup")

    controller = hass.data[DOMAIN]["controller"]

    for inverter in controller.inverters:
        controller.sensor_entities[
            inverter.serial_number + "_soc"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "State of Charge",
            "SoC",
            "mdi:battery",
            unitOfMeasurement=PERCENTAGE,
            deviceClass=SensorDeviceClass.BATTERY,
            decimals=0,
        )

        controller.sensor_entities[
            inverter.serial_number + "_pv_power"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "PV Power",
            "pv_power",
            "mdi:solar-power",
            unitOfMeasurement=UnitOfPower.KILO_WATT,
            deviceClass=SensorDeviceClass.POWER,
            decimals=2,
        )

        controller.sensor_entities[
            inverter.serial_number + "_mppt1_power"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "MPPT1 Power",
            "mppt1_power",
            "mdi:solar-power",
            unitOfMeasurement=UnitOfPower.KILO_WATT,
            deviceClass=SensorDeviceClass.POWER,
            decimals=2,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_mppt2_power"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "MPPT2 Power",
            "mppt2_power",
            "mdi:solar-power",
            unitOfMeasurement=UnitOfPower.KILO_WATT,
            deviceClass=SensorDeviceClass.POWER,
            decimals=2,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_battery_load"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Battery Load",
            "battery_load",
            "mdi:battery-minus-variant",
            unitOfMeasurement=UnitOfPower.KILO_WATT,
            deviceClass=SensorDeviceClass.POWER,
            decimals=2,
        )

        controller.sensor_entities[
            inverter.serial_number + "_grid_load"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Grid Load",
            "grid_load",
            "mdi:transmission-tower",
            unitOfMeasurement=UnitOfPower.KILO_WATT,
            deviceClass=SensorDeviceClass.POWER,
            decimals=2,
        )

        controller.sensor_entities[
            inverter.serial_number + "_grid_tied_load"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Current Load",
            "grid_tied_load",
            "mdi:home-lightning-bolt",
            unitOfMeasurement=UnitOfPower.KILO_WATT,
            deviceClass=SensorDeviceClass.POWER,
            decimals=2,
        )

        controller.sensor_entities[
            inverter.serial_number + "_eps_load"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "EPS Load",
            "eps_load",
            "mdi:power-socket",
            unitOfMeasurement=UnitOfPower.KILO_WATT,
            deviceClass=SensorDeviceClass.POWER,
            decimals=2,
        )

        controller.sensor_entities[
            inverter.serial_number + "_inverter_load"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Inverter Load",
            "inverter_load",
            "mdi:flash",
            unitOfMeasurement=UnitOfPower.KILO_WATT,
            deviceClass=SensorDeviceClass.POWER,
            decimals=2,
        )

        controller.sensor_entities[
            inverter.serial_number + "_pv_energy_today"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "PV Energy Today",
            "pv_energy_today",
            "mdi:solar-power-variant",
            unitOfMeasurement=UnitOfEnergy.KILO_WATT_HOUR,
            deviceClass=SensorDeviceClass.ENERGY,
            stateClass=SensorStateClass.TOTAL_INCREASING,
            decimals=2,
        )

        controller.sensor_entities[
            inverter.serial_number + "_pv_energy_total"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "PV Energy Total",
            "pv_energy_total",
            "mdi:solar-power-variant",
            unitOfMeasurement=UnitOfEnergy.KILO_WATT_HOUR,
            deviceClass=SensorDeviceClass.ENERGY,
            stateClass=SensorStateClass.TOTAL_INCREASING,
            decimals=0,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_grid_energy_in_total"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Grid Energy In Total",
            "grid_energy_in_total",
            "mdi:transmission-tower-export",
            unitOfMeasurement=UnitOfEnergy.KILO_WATT_HOUR,
            deviceClass=SensorDeviceClass.ENERGY,
            stateClass=SensorStateClass.TOTAL_INCREASING,
            decimals=2,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_grid_energy_out_total"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Grid Energy Out Total",
            "grid_energy_out_total",
            "mdi:transmission-tower-import",
            unitOfMeasurement=UnitOfEnergy.KILO_WATT_HOUR,
            deviceClass=SensorDeviceClass.ENERGY,
            stateClass=SensorStateClass.TOTAL_INCREASING,
            decimals=2,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_grid_energy_in_today"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Grid Energy In Today",
            "grid_energy_in_today",
            "mdi:transmission-tower-export",
            unitOfMeasurement=UnitOfEnergy.KILO_WATT_HOUR,
            deviceClass=SensorDeviceClass.ENERGY,
            stateClass=SensorStateClass.TOTAL_INCREASING,
            decimals=2,
        )

        controller.sensor_entities[
            inverter.serial_number + "_grid_energy_out_today"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Grid Energy Out Today",
            "grid_energy_out_today",
            "mdi:transmission-tower-import",
            unitOfMeasurement=UnitOfEnergy.KILO_WATT_HOUR,
            deviceClass=SensorDeviceClass.ENERGY,
            stateClass=SensorStateClass.TOTAL_INCREASING,
            decimals=2,
        )

        controller.sensor_entities[
            inverter.serial_number + "_battery_energy_out_total"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Battery Energy Out Total",
            "battery_energy_out_total",
            "mdi:battery-minus",
            unitOfMeasurement=UnitOfEnergy.KILO_WATT_HOUR,
            deviceClass=SensorDeviceClass.ENERGY,
            stateClass=SensorStateClass.TOTAL_INCREASING,
            decimals=2,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_battery_energy_in_total"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Battery Energy In Total",
            "battery_energy_in_total",
            "mdi:battery-plus",
            unitOfMeasurement=UnitOfEnergy.KILO_WATT_HOUR,
            deviceClass=SensorDeviceClass.ENERGY,
            stateClass=SensorStateClass.TOTAL_INCREASING,
            decimals=2,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_battery_energy_out_today"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Battery Energy Out Today",
            "battery_energy_out_today",
            "mdi:battery-minus",
            unitOfMeasurement=UnitOfEnergy.KILO_WATT_HOUR,
            deviceClass=SensorDeviceClass.ENERGY,
            stateClass=SensorStateClass.TOTAL_INCREASING,
            decimals=2,
        )

        controller.sensor_entities[
            inverter.serial_number + "_battery_energy_in_today"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Battery Energy In Today",
            "battery_energy_in_today",
            "mdi:battery-plus",
            unitOfMeasurement=UnitOfEnergy.KILO_WATT_HOUR,
            deviceClass=SensorDeviceClass.ENERGY,
            stateClass=SensorStateClass.TOTAL_INCREASING,
            decimals=2,
        )

        controller.sensor_entities[
            inverter.serial_number + "_battery_current"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Battery Current",
            "battery_current",
            "mdi:current-dc",
            unitOfMeasurement=UnitOfElectricCurrent.AMPERE,
            deviceClass=SensorDeviceClass.CURRENT,
            decimals=2,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_grid_current"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Grid Current",
            "grid_current",
            "mdi:current-ac",
            unitOfMeasurement=UnitOfElectricCurrent.AMPERE,
            deviceClass=SensorDeviceClass.CURRENT,
            decimals=2,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_mppt1_current"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "MPPT1 Current",
            "mppt1_current",
            "mdi:current-dc",
            unitOfMeasurement=UnitOfElectricCurrent.AMPERE,
            deviceClass=SensorDeviceClass.CURRENT,
            decimals=2,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_mppt2_current"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "MPPT2 Current",
            "mppt2_current",
            "mdi:current-dc",
            unitOfMeasurement=UnitOfElectricCurrent.AMPERE,
            deviceClass=SensorDeviceClass.CURRENT,
            decimals=2,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_battery_voltage"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Battery Voltage",
            "battery_voltage",
            "mdi:lightning-bolt",
            unitOfMeasurement=UnitOfElectricPotential.VOLT,
            deviceClass=SensorDeviceClass.VOLTAGE,
            decimals=1,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_grid_voltage"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Grid Voltage",
            "grid_voltage",
            "mdi:lightning-bolt",
            unitOfMeasurement=UnitOfElectricPotential.VOLT,
            deviceClass=SensorDeviceClass.VOLTAGE,
            decimals=1,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_mppt1_voltage"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "MPPT1 Voltage",
            "mppt1_voltage",
            "mdi:lightning-bolt",
            unitOfMeasurement=UnitOfElectricPotential.VOLT,
            deviceClass=SensorDeviceClass.VOLTAGE,
            decimals=1,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_mppt2_voltage"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "MPPT2 Voltage",
            "mppt2_voltage",
            "mdi:lightning-bolt",
            unitOfMeasurement=UnitOfElectricPotential.VOLT,
            deviceClass=SensorDeviceClass.VOLTAGE,
            decimals=1,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_system_temp"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "System Temp",
            "system_temp",
            "mdi:temperature-celsius",
            unitOfMeasurement=UnitOfTemperature.CELSIUS,
            deviceClass=SensorDeviceClass.TEMPERATURE,
            decimals=0,
            category=EntityCategory.DIAGNOSTIC,
        )

        controller.sensor_entities[
            inverter.serial_number + "_master_software_version"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Version Master",
            "master_software_version",
            "mdi:code-block-braces",
            category=EntityCategory.DIAGNOSTIC,
            deviceClass=None,
            unitOfMeasurement=None,
            stateClass=None,
        )

        controller.sensor_entities[
            inverter.serial_number + "_slave_software_version"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Version Slave",
            "slave_software_version",
            "mdi:code-block-brackets",
            category=EntityCategory.DIAGNOSTIC,
            deviceClass=None,
            unitOfMeasurement=None,
            stateClass=None,
        )

        controller.sensor_entities[
            inverter.serial_number + "_ems_software_version"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Version EMS",
            "ems_software_version",
            "mdi:code-block-parentheses",
            category=EntityCategory.DIAGNOSTIC,
            deviceClass=None,
            unitOfMeasurement=None,
            stateClass=None,
        )

        controller.sensor_entities[
            inverter.serial_number + "_dcdc_software_version"
        ] = InverterSensorEntity(
            hass,
            controller,
            inverter,
            "Version DC-DC",
            "dcdc_software_version",
            "mdi:code-block-tags",
            category=EntityCategory.DIAGNOSTIC,
            deviceClass=None,
            unitOfMeasurement=None,
            stateClass=None,
        )

        # No point in the below as the inverter is always returning zero until Skylinefix it.
        # controller.sensor_entities[
        #    inverter.serial_number + "_battery_temp"
        # ] = InverterSensorEntity(
        #    hass,
        #    controller,
        #    inverter,
        #    "Battery Temp",
        #    "battery_temp",
        #    "mdi:temperature-celsius",
        #    unitOfMeasurement=UnitOfTemperature.CELSIUS,
        #    deviceClass=SensorDeviceClass.TEMPERATURE,
        #    decimals=0,
        #    category=EntityCategory.DIAGNOSTIC,
        # )

    controller.sensor_entities["skyline_consumer_load"] = InverterSensorEntity(
        hass,
        controller,
        None,
        "Skyline Consumer Load",
        "consumer_load",
        "mdi:power-socket",
        unitOfMeasurement=UnitOfPower.KILO_WATT,
        deviceClass=SensorDeviceClass.POWER,
        decimals=2,
    )

    controller.sensor_entities[
        "skyline_average_excess_pv_power"
    ] = InverterSensorEntity(
        hass,
        controller,
        None,
        "Skyline Excess PV Power",
        "average_excess_pv_power",
        "mdi:sun-wireless",
        unitOfMeasurement=UnitOfPower.KILO_WATT,
        deviceClass=SensorDeviceClass.POWER,
        decimals=2,
    )

    if len(controller.inverters) > 1:
        controller.sensor_entities["skyline_pv_power"] = InverterSensorEntity(
            hass,
            controller,
            None,
            "Skyline PV Power",
            "pv_power",
            "mdi:solar-power",
            unitOfMeasurement=UnitOfPower.KILO_WATT,
            deviceClass=SensorDeviceClass.POWER,
            decimals=2,
        )

        controller.sensor_entities["skyline_battery_load"] = InverterSensorEntity(
            hass,
            controller,
            None,
            "Skyline Battery Load",
            "battery_load",
            "mdi:battery-minus-variant",
            unitOfMeasurement=UnitOfPower.KILO_WATT,
            deviceClass=SensorDeviceClass.POWER,
            decimals=2,
        )

        controller.sensor_entities["skyline_grid_load"] = InverterSensorEntity(
            hass,
            controller,
            None,
            "Skyline Grid Load",
            "grid_load",
            "mdi:transmission-tower",
            unitOfMeasurement=UnitOfPower.KILO_WATT,
            deviceClass=SensorDeviceClass.POWER,
            decimals=2,
        )

        controller.sensor_entities["skyline_grid_tied_load"] = InverterSensorEntity(
            hass,
            controller,
            None,
            "Skyline Current Load",
            "grid_tied_load",
            "mdi:home-lightning-bolt",
            unitOfMeasurement=UnitOfPower.KILO_WATT,
            deviceClass=SensorDeviceClass.POWER,
            decimals=2,
        )

        controller.sensor_entities["skyline_eps_load"] = InverterSensorEntity(
            hass,
            controller,
            None,
            "Skyline EPS Load",
            "eps_load",
            "mdi:power-socket",
            unitOfMeasurement=UnitOfPower.KILO_WATT,
            deviceClass=SensorDeviceClass.POWER,
            decimals=2,
        )

        controller.sensor_entities["skyline_inverter_load"] = InverterSensorEntity(
            hass,
            controller,
            None,
            "Skyline Inverter Load",
            "inverter_load",
            "mdi:flash",
            unitOfMeasurement=UnitOfPower.KILO_WATT,
            deviceClass=SensorDeviceClass.POWER,
            decimals=2,
        )

    entities = controller.get_sensor_entities()

    async_add_entities(entities)

    await controller.setup_done("sensor")


class InverterSensorEntity(SensorEntity):
    """The main Inverter sensor."""

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
        decimals=-1,
        category=None,
    ) -> None:
        """Inverter sensor intialiser."""
        self.currentValue = None

        if inverter is not None:
            self.inverter = inverter
            self._attr_device_info = inverter.device_info
            self._attr_unique_id = inverter.serial_number + "_" + entityType
            entity_id = generate_entity_id(
                "sensor.{}",
                inverter.serial_number + "_" + entityType,
                [],
                self.hass,
            )
        else:
            entity_id = generate_entity_id(
                "sensor.{}",
                "skyline_" + entityType,
                [],
                self.hass,
            )
            self._attr_unique_id = "skyline_" + entityType

        self.controller = controller
        self.hass = hass
        self.entity_id = entity_id

        # self._entity_name = entityName
        self._attr_name = entityName
        self._attr_has_entity_name = True

        self._attr_translation_key: str = entityType.lower()

        self._attr_native_unit_of_measurement = unitOfMeasurement
        self._attr_native_device_class = deviceClass
        self._attr_device_class = deviceClass
        self._attr_state_class = stateClass
        self._attr_icon = icon

        if stateClass == SensorStateClass.TOTAL:
            self._attr_last_reset = 0

        if category is not None:
            self._attr_entity_category = category

        if decimals >= 0:
            self._attr_suggested_display_precision = decimals

    def set_native_value(self, new_state) -> None:
        """Set the HA value from the modbus response."""
        if self.currentValue is not None and self.currentValue == new_state:
            # avoid noise...
            return

        self.currentValue = new_state

        self._attr_native_value = new_state
        self.async_write_ha_state()
