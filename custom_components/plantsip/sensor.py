"""Sensor platform for PlantSip."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

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
        
    @property
    def unique_id(self):
        """Return unique ID for the sensor."""
        return f"{self._device_id}_moisture_{self._channel_index}"
        
    @property
    def name(self):
        """Return the name of the sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} Channel {self._channel_index} Moisture"

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
        
    @property
    def unique_id(self):
        """Return unique ID for the sensor."""
        return f"{self._device_id}_water_level"
        
    @property
    def name(self):
        """Return the name of the sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} Water Level"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data[self._device_id]["status"]["water_level"]
