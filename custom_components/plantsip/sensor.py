"""Sensor platform for PlantSip."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, MANUFACTURER

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the PlantSip sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = []
    for device_id, device_data in coordinator.data.items():
        # Add moisture sensor for each channel
        for channel in device_data["device"]["channels"]:
            entities.append(
                PlantSipMoistureSensor(
                    coordinator,
                    device_id,
                    channel["channel_index"],
                )
            )
        
        # Add water level sensor
        entities.append(
            PlantSipWaterLevelSensor(coordinator, device_id)
        )
        
        # Add battery sensors
        entities.extend([
            PlantSipBatteryVoltageSensor(coordinator, device_id),
            PlantSipBatteryLevelSensor(coordinator, device_id),
            PlantSipPowerSupplySensor(coordinator, device_id),
            PlantSipBatteryChargingSensor(coordinator, device_id),
        ])
    
    async_add_entities(entities)

class PlantSipMoistureSensor(CoordinatorEntity, SensorEntity):
    """Representation of a moisture sensor."""

    def __init__(self, coordinator, device_id, channel_index):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._channel_index = channel_index
        self._attr_device_class = SensorDeviceClass.MOISTURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "%"
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:water-percent"
        
        device_data = coordinator.data[device_id]["device"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_data["name"],
            manufacturer=MANUFACTURER,
            model="PlantSip Device",
            sw_version=coordinator.data[device_id]["status"]["firmware_version"],
        )
        
    @property
    def unique_id(self):
        """Return unique ID for the sensor."""
        return f"{self._device_id}_moisture_{self._channel_index}"
        
    @property
    def name(self):
        """Return the name of the sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} Channel {self._channel_index} {self.translation_key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "moisture"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data[self._device_id]["status"]["moisture_readings"].get(
            str(self._channel_index)
        )

class PlantSipWaterLevelSensor(CoordinatorEntity, SensorEntity):
    """Representation of a water level sensor."""

    def __init__(self, coordinator, device_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "%"
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:gauge"
        
        device_data = coordinator.data[device_id]["device"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_data["name"],
            manufacturer=MANUFACTURER,
            model="PlantSip Device",
            sw_version=coordinator.data[device_id]["status"]["firmware_version"],
        )
        
    @property
    def unique_id(self):
        """Return unique ID for the sensor."""
        return f"{self._device_id}_water_level"
        
    @property
    def name(self):
        """Return the name of the sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} {self.translation_key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "water_level"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data[self._device_id]["status"]["water_level"]


class PlantSipBatteryVoltageSensor(CoordinatorEntity, SensorEntity):
    """Representation of a battery voltage sensor."""

    def __init__(self, coordinator, device_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "V"
        self._attr_suggested_display_precision = 2
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:battery-charging-100"
        
        device_data = coordinator.data[device_id]["device"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_data["name"],
            manufacturer=MANUFACTURER,
            model="PlantSip Device",
            sw_version=coordinator.data[device_id]["status"]["firmware_version"],
        )
        
    @property
    def unique_id(self):
        """Return unique ID for the sensor."""
        return f"{self._device_id}_battery_voltage"
        
    @property
    def name(self):
        """Return the name of the sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} {self.translation_key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "battery_voltage"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data[self._device_id]["status"]["battery_voltage"]


class PlantSipBatteryLevelSensor(CoordinatorEntity, SensorEntity):
    """Representation of a battery level sensor."""

    def __init__(self, coordinator, device_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "%"
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        
        device_data = coordinator.data[device_id]["device"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_data["name"],
            manufacturer=MANUFACTURER,
            model="PlantSip Device",
            sw_version=coordinator.data[device_id]["status"]["firmware_version"],
        )
        
    @property
    def unique_id(self):
        """Return unique ID for the sensor."""
        return f"{self._device_id}_battery_level"
        
    @property
    def name(self):
        """Return the name of the sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} Battery Level"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data[self._device_id]["status"]["battery_level"]


class PlantSipPowerSupplySensor(CoordinatorEntity, SensorEntity):
    """Representation of a power supply sensor."""

    def __init__(self, coordinator, device_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["connected", "disconnected"]
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:power-plug"
        
    @property
    def unique_id(self):
        """Return unique ID for the sensor."""
        return f"{self._device_id}_power_supply"
        
    @property
    def name(self):
        """Return the name of the sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} Power Supply"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return "connected" if self.coordinator.data[self._device_id]["status"]["power_supply_connected"] else "disconnected"


class PlantSipBatteryChargingSensor(CoordinatorEntity, SensorEntity):
    """Representation of a battery charging sensor."""

    def __init__(self, coordinator, device_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["charging", "not_charging"]
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:battery-charging"
        
    @property
    def unique_id(self):
        """Return unique ID for the sensor."""
        return f"{self._device_id}_battery_charging"
        
    @property
    def name(self):
        """Return the name of the sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} Battery Charging"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return "charging" if self.coordinator.data[self._device_id]["status"]["battery_charging"] else "not_charging"
