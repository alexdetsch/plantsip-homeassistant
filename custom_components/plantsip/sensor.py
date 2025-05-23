"""Sensor platform for PlantSip."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional
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

_LOGGER = logging.getLogger(__name__)

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
        for channel_data in channels:
            channel_id = channel_data.get("id")
            channel_display_idx = channel_data.get("channel_index")
            if channel_id is not None and channel_display_idx is not None:
                entities.append(
                    PlantSipMoistureSensor(
                        coordinator,
                        device_id,
                        channel_id,
                        channel_display_idx,
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
        for channel_data in channels:
            channel_id = channel_data.get("id")
            channel_display_idx = channel_data.get("channel_index")
            if channel_id is not None and channel_display_idx is not None:
                entities.extend([
                    PlantSipLastWateredSensor(coordinator, device_id, channel_id, channel_display_idx),
                    PlantSipLastWateringAmountSensor(coordinator, device_id, channel_id, channel_display_idx),
                ])
            
        # Add firmware version sensor
        entities.append(
            PlantSipFirmwareVersionSensor(coordinator, device_id)
        )
    
    async_add_entities(entities)

class PlantSipMoistureSensor(CoordinatorEntity, SensorEntity):
    """Representation of a moisture sensor."""

    def __init__(self, coordinator, device_id, channel_id, channel_display_index):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._channel_id = channel_id  # Store the database PK for the channel
        self._channel_display_index = channel_display_index # Store the user-facing channel index
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
        # Using display index for UIDs to maintain consistency if it's unique per device.
        return f"{self._device_id}_moisture_{self._channel_display_index}"
        
    @property
    def name(self):
        """Return the name of the sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} Channel {self._channel_display_index} {self.translation_key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "moisture"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self.available:
            return None
        
        try:
            status_data = self.coordinator.data[self._device_id]["status"]
            channels_data = status_data.get("channels", {})
            
            if not isinstance(channels_data, dict):
                _LOGGER.warning("Invalid channels data format for device %s", self._device_id)
                return None
                
            channel_status_data = channels_data.get(str(self._channel_id))
            if not channel_status_data or not isinstance(channel_status_data, dict):
                return None
                
            moisture_level = channel_status_data.get("moisture_level")
            if moisture_level is not None:
                # Ensure moisture level is within reasonable bounds (0-100%)
                if isinstance(moisture_level, (int, float)):
                    return max(0, min(100, float(moisture_level)))
                    
            return None
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.warning("Error getting moisture level for device %s channel %d: %s", 
                          self._device_id, self._channel_display_index, err)
            return None

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
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if not self.available:
            return None
            
        try:
            firmware_version = self.coordinator.data[self._device_id]["status"].get("firmware_version")
            if firmware_version and isinstance(firmware_version, str):
                return firmware_version.strip()
            return "Unknown"
        except (KeyError, TypeError) as err:
            _LOGGER.warning("Error getting firmware version for device %s: %s", self._device_id, err)
            return "Unknown"

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
        # self._attr_state_class = SensorStateClass.MEASUREMENT  <- Removed as it's incompatible with SensorDeviceClass.WATER
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
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self.available:
            return None
            
        try:
            water_level = self.coordinator.data[self._device_id]["status"].get("water_level")
            if water_level is not None and isinstance(water_level, (int, float)):
                # Ensure water level is within reasonable bounds (0-100%)
                return max(0, min(100, float(water_level)))
            return None
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.warning("Error getting water level for device %s: %s", self._device_id, err)
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._device_id in self.coordinator.data
            and self.coordinator.data[self._device_id].get("available", False)
        )


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
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self.available:
            return None
            
        try:
            voltage = self.coordinator.data[self._device_id]["status"].get("battery_voltage")
            if voltage is not None and isinstance(voltage, (int, float)):
                # Reasonable voltage range for battery
                voltage_float = float(voltage)
                if 0 <= voltage_float <= 20:  # 20V is a reasonable upper limit
                    return round(voltage_float, 2)
            return None
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.warning("Error getting battery voltage for device %s: %s", self._device_id, err)
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._device_id in self.coordinator.data
            and self.coordinator.data[self._device_id].get("available", False)
        )


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
        return f"{device_name} {self.translation_key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "battery_level"

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self.available:
            return None
            
        try:
            battery_level = self.coordinator.data[self._device_id]["status"].get("battery_level")
            if battery_level is not None and isinstance(battery_level, (int, float)):
                # Ensure battery level is within 0-100%
                return max(0, min(100, int(float(battery_level))))
            return None
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.warning("Error getting battery level for device %s: %s", self._device_id, err)
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._device_id in self.coordinator.data
            and self.coordinator.data[self._device_id].get("available", False)
        )


class PlantSipLastWateredSensor(CoordinatorEntity, SensorEntity):
    """Representation of a last watered timestamp sensor."""

    def __init__(self, coordinator, device_id, channel_id, channel_display_index):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._channel_id = channel_id
        self._channel_display_index = channel_display_index
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
    def unique_id(self) -> str:
        """Return unique ID for the sensor."""
        return f"{self._device_id}_last_watered_{self._channel_display_index}"
        
    @property
    def name(self):
        """Return the name of the sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} Channel {self._channel_display_index} {self.translation_key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "last_watered"

    @property
    def native_value(self) -> Optional[datetime]:
        """Return the state of the sensor."""
        if not self.available:
            return None
            
        try:
            status_data = self.coordinator.data[self._device_id]["status"]
            channels_data = status_data.get("channels", {})
            
            if not isinstance(channels_data, dict):
                return None
                
            channel_status_data = channels_data.get(str(self._channel_id))
            if not channel_status_data or not isinstance(channel_status_data, dict):
                return None
                
            timestamp_str = channel_status_data.get("last_watered")
            if not timestamp_str or not isinstance(timestamp_str, str):
                return None
                
            # Parse the timestamp and ensure it has timezone info
            try:
                timestamp_str = timestamp_str.strip()
                # If the timestamp already contains timezone info, parse it directly
                if 'Z' in timestamp_str:
                    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                elif '+' in timestamp_str or timestamp_str.endswith('00:00'):
                    return datetime.fromisoformat(timestamp_str)
                else:
                    # Otherwise, assume UTC and add timezone info
                    return datetime.fromisoformat(timestamp_str).replace(tzinfo=pytz.UTC)
            except (ValueError, TypeError) as parse_err:
                _LOGGER.warning("Error parsing timestamp '%s' for device %s channel %d: %s", 
                              timestamp_str, self._device_id, self._channel_display_index, parse_err)
                return None
                
        except (KeyError, TypeError) as err:
            _LOGGER.warning("Error getting last watered time for device %s channel %d: %s", 
                          self._device_id, self._channel_display_index, err)
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

    def __init__(self, coordinator, device_id, channel_id, channel_display_index):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._channel_id = channel_id
        self._channel_display_index = channel_display_index
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
    def unique_id(self) -> str:
        """Return unique ID for the sensor."""
        return f"{self._device_id}_last_watering_amount_{self._channel_display_index}"
        
    @property
    def name(self):
        """Return the name of the sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} Channel {self._channel_display_index} {self.translation_key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "last_watering_amount"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self.available:
            return None
            
        try:
            status_data = self.coordinator.data[self._device_id]["status"]
            channels_data = status_data.get("channels", {})
            
            if not isinstance(channels_data, dict):
                return None
                
            channel_status_data = channels_data.get(str(self._channel_id))
            if not channel_status_data or not isinstance(channel_status_data, dict):
                return None
                
            watering_amount = channel_status_data.get("last_watering_amount")
            if watering_amount is not None and isinstance(watering_amount, (int, float)):
                amount_float = float(watering_amount)
                # Reasonable range for watering amount (0-10000ml)
                if 0 <= amount_float <= 10000:
                    return round(amount_float, 1)
                    
            return None
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.warning("Error getting last watering amount for device %s channel %d: %s", 
                          self._device_id, self._channel_display_index, err)
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._device_id in self.coordinator.data
            and self.coordinator.data[self._device_id].get("available", False)
        )

