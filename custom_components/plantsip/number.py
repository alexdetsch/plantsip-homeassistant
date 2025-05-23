"""Number platform for PlantSip."""
from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo, EntityCategory

from .const import DOMAIN, MANUFACTURER, MIN_WATER_AMOUNT, MAX_WATER_AMOUNT

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the PlantSip number entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = []
    for device_id, device_data in coordinator.data.items():
        if not device_data.get("available", False):
            continue
            
        device = device_data.get("device", {})
        channels = device.get("channels", [])
        
        for channel_data in channels:
            channel_id = channel_data.get("id")
            channel_display_idx = channel_data.get("channel_index")
            if channel_id is not None and channel_display_idx is not None:
                entities.extend([
                    PlantSipManualWaterAmountNumber(
                        coordinator,
                        device_id,
                        channel_id,
                        channel_display_idx,
                    ),
                    PlantSipAutomaticWaterAmountNumber(
                        coordinator,
                        device_id,
                        channel_id,
                        channel_display_idx,
                    ),
                ])
    
    async_add_entities(entities)

class PlantSipManualWaterAmountNumber(CoordinatorEntity, NumberEntity):
    """Representation of a manual water amount number entity."""

    def __init__(self, coordinator, device_id, channel_id, channel_display_index):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._channel_id = channel_id
        self._channel_display_index = channel_display_index
        self._attr_native_min_value = MIN_WATER_AMOUNT
        self._attr_native_max_value = MAX_WATER_AMOUNT
        self._attr_native_step = 1.0
        self._attr_native_unit_of_measurement = "ml"
        self._attr_mode = NumberMode.BOX
        self._attr_icon = "mdi:water"
        
        device_data = coordinator.data[device_id]["device"]
        firmware_version = coordinator.data[device_id]["status"].get("firmware_version", "Unknown")
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_data["name"],
            manufacturer=MANUFACTURER,
            model="PlantSip Device",
            sw_version=firmware_version,
        )
        
    @property
    def unique_id(self) -> str:
        """Return unique ID for the number entity."""
        return f"{self._device_id}_manual_water_amount_{self._channel_display_index}"
        
    @property
    def name(self) -> str:
        """Return the name of the number entity."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} Channel {self._channel_display_index} {self.translation_key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "manual_water_amount"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        if not self.available:
            return 50.0  # Default value
            
        channel_data = self._get_channel_data()
        return channel_data.get("manual_water_amount", 50.0)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not (self.coordinator.last_update_success
                and self._device_id in self.coordinator.data
                and self.coordinator.data[self._device_id].get("available", False)):
            return False
            
        # Check if channel still exists
        return any(
            ch.get("id") == self._channel_id 
            for ch in self.coordinator.data[self._device_id]["device"].get("channels", [])
        )

    def _get_channel_data(self) -> Dict[str, Any]:
        """Get channel data from coordinator."""
        if not self.available:
            return {}
            
        return next(
            (ch_data for ch_data in self.coordinator.data[self._device_id]["device"]["channels"]
             if ch_data.get("id") == self._channel_id),
            {}
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        if not self.available:
            _LOGGER.error("Device %s is not available for manual water amount setting", self._device_id)
            return
            
        if not (MIN_WATER_AMOUNT <= value <= MAX_WATER_AMOUNT):
            _LOGGER.error("Invalid manual water amount %.1f for device %s channel %d (must be %d-%dml)", 
                        value, self._device_id, self._channel_display_index, MIN_WATER_AMOUNT, MAX_WATER_AMOUNT)
            return
            
        try:
            success = await self.coordinator.async_update_channel_config(
                self._device_id, 
                self._channel_id, 
                {"manual_water_amount": value}
            )
            
            if success:
                _LOGGER.info("Updated manual water amount to %.1fml for device %s channel %d", 
                           value, self._device_id, self._channel_display_index)
            else:
                _LOGGER.error("Failed to update manual water amount for device %s channel %d", 
                            self._device_id, self._channel_display_index)
        except Exception as err:
            _LOGGER.error("Error setting manual water amount for device %s channel %d: %s", 
                        self._device_id, self._channel_display_index, err)

class PlantSipAutomaticWaterAmountNumber(CoordinatorEntity, NumberEntity):
    """Representation of an automatic water amount number entity."""

    def __init__(self, coordinator, device_id, channel_id, channel_display_index):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._channel_id = channel_id
        self._channel_display_index = channel_display_index
        self._attr_native_min_value = MIN_WATER_AMOUNT
        self._attr_native_max_value = MAX_WATER_AMOUNT
        self._attr_native_step = 1.0
        self._attr_native_unit_of_measurement = "ml"
        self._attr_mode = NumberMode.BOX
        self._attr_icon = "mdi:water-sync"
        self._attr_entity_category = EntityCategory.CONFIG
        
        device_data = coordinator.data[device_id]["device"]
        firmware_version = coordinator.data[device_id]["status"].get("firmware_version", "Unknown")
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_data["name"],
            manufacturer=MANUFACTURER,
            model="PlantSip Device",
            sw_version=firmware_version,
        )
        
    @property
    def unique_id(self) -> str:
        """Return unique ID for the number entity."""
        return f"{self._device_id}_automatic_water_amount_{self._channel_display_index}"
        
    @property
    def name(self) -> str:
        """Return the name of the number entity."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} Channel {self._channel_display_index} {self.translation_key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "automatic_water_amount"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        if not self.available:
            return 50.0  # Default value
            
        channel_data = self._get_channel_data()
        return channel_data.get("automatic_water_amount", 50.0)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not (self.coordinator.last_update_success
                and self._device_id in self.coordinator.data
                and self.coordinator.data[self._device_id].get("available", False)):
            return False
            
        # Check if channel still exists
        return any(
            ch.get("id") == self._channel_id 
            for ch in self.coordinator.data[self._device_id]["device"].get("channels", [])
        )

    def _get_channel_data(self) -> Dict[str, Any]:
        """Get channel data from coordinator."""
        if not self.available:
            return {}
            
        return next(
            (ch_data for ch_data in self.coordinator.data[self._device_id]["device"]["channels"]
             if ch_data.get("id") == self._channel_id),
            {}
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        if not self.available:
            _LOGGER.error("Device %s is not available for automatic water amount setting", self._device_id)
            return
            
        if not (MIN_WATER_AMOUNT <= value <= MAX_WATER_AMOUNT):
            _LOGGER.error("Invalid automatic water amount %.1f for device %s channel %d (must be %d-%dml)", 
                        value, self._device_id, self._channel_display_index, MIN_WATER_AMOUNT, MAX_WATER_AMOUNT)
            return
            
        try:
            success = await self.coordinator.async_update_channel_config(
                self._device_id, 
                self._channel_id, 
                {"automatic_water_amount": value}
            )
            
            if success:
                _LOGGER.info("Updated automatic water amount to %.1fml for device %s channel %d", 
                           value, self._device_id, self._channel_display_index)
            else:
                _LOGGER.error("Failed to update automatic water amount for device %s channel %d", 
                            self._device_id, self._channel_display_index)
        except Exception as err:
            _LOGGER.error("Error setting automatic water amount for device %s channel %d: %s", 
                        self._device_id, self._channel_display_index, err)