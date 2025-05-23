"""Switch platform for PlantSip."""
from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import entity_platform
import voluptuous as vol

from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the PlantSip switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    
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
                entities.append(
                    PlantSipWateringSwitch(
                        coordinator,
                        api,
                        device_id,
                        channel_id,
                        channel_display_idx,
                    )
                )
    
    async_add_entities(entities)
    
    # Register services
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "set_water_amount",
        {
            vol.Required("amount"): vol.All(vol.Coerce(float), vol.Range(min=1, max=10000))
        },
        "async_set_water_amount"
    )

class PlantSipWateringSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a watering switch."""

    def __init__(self, coordinator, api, device_id, channel_id, channel_display_index):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._api = api
        self._device_id = device_id
        self._channel_id = channel_id
        self._channel_display_index = channel_display_index
        self._is_on = False
        self._last_watering_time = None
        self._watering_in_progress = False
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
    def unique_id(self):
        """Return unique ID for the switch."""
        # Using display index for UIDs to maintain consistency if it's unique per device.
        return f"{self._device_id}_watering_{self._channel_display_index}"
        
    @property
    def name(self):
        """Return the name of the switch."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} Channel {self._channel_display_index} {self.translation_key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "watering"

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._is_on or self._watering_in_progress

    @property
    def icon(self):
        """Return the icon."""
        if self._watering_in_progress:
            return "mdi:water-pump"
        return "mdi:water" if self.is_on else "mdi:water-off"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not (self.coordinator.last_update_success
                and self._device_id in self.coordinator.data
                and self.coordinator.data[self._device_id].get("available", False)):
            return False
            
        # Check if channel still exists
        channel_exists = any(
            ch.get("id") == self._channel_id 
            for ch in self.coordinator.data[self._device_id]["device"].get("channels", [])
        )
        
        return channel_exists

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        if not self.available:
            return {}
            
        channel_device_data = self._get_channel_data()
        attributes = {
            "manual_water_amount": channel_device_data.get("manual_water_amount", 50.0),
            "automatic_water_amount": channel_device_data.get("automatic_water_amount", 50.0),
            "flow_rate_pump": channel_device_data.get("flow_rate_pump", 0),
            "desired_moisture_level": channel_device_data.get("desired_moisture_level"),
            "watering_in_progress": self._watering_in_progress,
        }
        
        if self._last_watering_time:
            attributes["last_watering_time"] = self._last_watering_time.isoformat()
            
        return attributes

    def _get_channel_data(self) -> Dict[str, Any]:
        """Get channel data from coordinator."""
        if not self.available:
            return {}
            
        return next(
            (ch_data for ch_data in self.coordinator.data[self._device_id]["device"]["channels"]
             if ch_data.get("id") == self._channel_id),
            {}
        )

    async def async_set_water_amount(self, amount: float) -> None:
        """Set the water amount for this channel."""
        if not self.available:
            _LOGGER.error("Device %s is not available for water amount setting", self._device_id)
            return
            
        if not (1 <= amount <= 10000):
            _LOGGER.error("Invalid water amount %.1f for device %s channel %d (must be 1-10000ml)", 
                        amount, self._device_id, self._channel_display_index)
            return
            
        try:
            # Update via API
            success = await self.coordinator.async_update_channel_config(
                self._device_id, 
                self._channel_id, 
                {"manual_water_amount": amount}
            )
            
            if success:
                _LOGGER.info("Updated water amount to %.1fml for device %s channel %d", 
                           amount, self._device_id, self._channel_display_index)
                self.async_write_ha_state()
            else:
                _LOGGER.error("Failed to update water amount for device %s channel %d", 
                            self._device_id, self._channel_display_index)
        except Exception as err:
            _LOGGER.error("Error setting water amount for device %s channel %d: %s", 
                        self._device_id, self._channel_display_index, err)

    async def async_turn_on(self, **kwargs):
        """Turn the switch on (trigger watering)."""
        if not self.available:
            _LOGGER.error("Device %s is not available", self._device_id)
            return

        if self._watering_in_progress:
            _LOGGER.warning("Watering already in progress for device %s channel %d", 
                          self._device_id, self._channel_display_index)
            return

        try:
            self._watering_in_progress = True
            self.async_write_ha_state()
            
            channel_device_data = self._get_channel_data()
            water_amount = channel_device_data.get("manual_water_amount", 50.0)
            
            if not (1 <= water_amount <= 10000):
                _LOGGER.error("Invalid water amount %.1f for device %s channel %d (must be 1-10000ml)", 
                            water_amount, self._device_id, self._channel_display_index)
                return
                
            success = await self.coordinator.async_trigger_watering(
                self._device_id,
                self._channel_id,
                water_amount,
            )
            
            if success:
                self._is_on = True
                from homeassistant.util import utcnow
                self._last_watering_time = utcnow()
                _LOGGER.info("Successfully triggered watering for device %s channel %d with %.1fml", 
                           self._device_id, self._channel_display_index, water_amount)
            else:
                _LOGGER.error("Failed to trigger watering for device %s channel %d", 
                            self._device_id, self._channel_display_index)
                self._is_on = False
                
        except Exception as error:
            _LOGGER.error("Error triggering watering for device %s channel %d: %s", 
                        self._device_id, self._channel_display_index, error)
            self._is_on = False
        finally:
            self._watering_in_progress = False
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off (this is just a visual state change)."""
        if not self._watering_in_progress:
            self._is_on = False
            self.async_write_ha_state()
        else:
            _LOGGER.warning("Cannot turn off switch while watering is in progress")
