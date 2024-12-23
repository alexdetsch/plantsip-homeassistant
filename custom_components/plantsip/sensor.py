"""Sensor platform for PlantSip."""
from __future__ import annotations

from datetime import datetime
import pytz
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
        if not device_data.get("available", False):
            continue
            
        device = device_data.get("device", {})
        channels = device.get("channels", [])
        
        # Add moisture sensor for each channel
        for channel in channels:
            channel_index = channel.get("channel_index")
            if channel_index is not None:
                entities.append(
                    PlantSipMoistureSensor(
                        coordinator,
                        device_id,
                        channel_index,
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
        ])
        
        # Add last watered sensors for each channel
        for channel in channels:
            channel_index = channel.get("channel_index")
            if channel_index is not None:
                entities.extend([
                    PlantSipLastWateredSensor(coordinator, device_id, channel_index),
                    PlantSipLastWateringAmountSensor(coordinator, device_id, channel_index),
                ])
            
        # Add firmware version sensor
        entities.append(
            PlantSipFirmwareVersionSensor(coordinator, device_id)
        )
    
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
        if not self.available:
            return None
        channel_data = self.coordinator.data[self._device_id]["status"]["channels"].get(
            str(self._channel_index)
        )
        return channel_data["moisture_level"] if channel_data else None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._device_id in self.coordinator.data
            and self.coordinator.data[self._device_id].get("available", False)
        )


class PlantSipFirmwareVersionSensor(CoordinatorEntity, SensorEntity):
    """Representation of a firmware version sensor."""

    def __init__(self, coordinator, device_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:cellphone-arrow-down"
        
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
        return f"{self._device_id}_firmware_version"
        
    @property
    def name(self):
        """Return the name of the sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} {self.translation_key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "firmware_version"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if not self.available:
            return None
        return self.coordinator.data[self._device_id]["status"]["firmware_version"]

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._device_id in self.coordinator.data
            and self.coordinator.data[self._device_id].get("available", False)
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


class PlantSipLastWateredSensor(CoordinatorEntity, SensorEntity):
    """Representation of a last watered timestamp sensor."""

    def __init__(self, coordinator, device_id, channel_index):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._channel_index = channel_index
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
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
        return f"{self._device_id}_last_watered_{self._channel_index}"
        
    @property
    def name(self):
        """Return the name of the sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} Channel {self._channel_index} {self.translation_key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "last_watered"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if not self.available:
            return None
        channel_data = self.coordinator.data[self._device_id]["status"]["channels"].get(
            str(self._channel_index)
        )
        if not channel_data or not channel_data.get("last_watered"):
            return None
            
        # Parse the timestamp and ensure it has timezone info
        try:
            timestamp = channel_data["last_watered"]
            # If the timestamp already contains timezone info, parse it directly
            if 'Z' in timestamp or '+' in timestamp:
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            # Otherwise, assume UTC and add timezone info
            return datetime.fromisoformat(timestamp).replace(tzinfo=pytz.UTC)
        except (ValueError, TypeError):
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._device_id in self.coordinator.data
            and self.coordinator.data[self._device_id].get("available", False)
        )


class PlantSipLastWateringAmountSensor(CoordinatorEntity, SensorEntity):
    """Representation of a last watering amount sensor."""

    def __init__(self, coordinator, device_id, channel_index):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._channel_index = channel_index
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = "ml"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_suggested_display_precision = 0
        
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
        return f"{self._device_id}_last_watering_duration_{self._channel_index}"
        
    @property
    def name(self):
        """Return the name of the sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} Channel {self._channel_index} {self.translation_key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "last_watering_amount"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if not self.available:
            return None
        channel_data = self.coordinator.data[self._device_id]["status"]["channels"].get(
            str(self._channel_index)
        )
        return channel_data["last_watering_amount"] if channel_data else None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._device_id in self.coordinator.data
            and self.coordinator.data[self._device_id].get("available", False)
        )

