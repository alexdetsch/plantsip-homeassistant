"""Switch platform for PlantSip."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

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

class PlantSipWateringSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a watering switch."""

    def __init__(self, coordinator, api, device_id, channel_id, channel_display_index):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._api = api
        self._device_id = device_id
        self._channel_id = channel_id # Store the database PK for the channel
        self._channel_display_index = channel_display_index # Store the user-facing channel index
        self._is_on = False
        self._attr_icon = "mdi:water" 
        
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
        return self._is_on

    @property
    def icon(self):
        """Return the icon."""
        return "mdi:water" if self.is_on else "mdi:water-off"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._device_id in self.coordinator.data
            and self.coordinator.data[self._device_id].get("available", False)
        )

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        if not self.available:
            return {}
            
        # device["channels"] stores a list of channel dicts from the API (DeviceSummary.channels items)
        # These dicts should have "id" (PK) and "manual_water_amount".
        channel_device_data = next(
            (ch_data for ch_data in self.coordinator.data[self._device_id]["device"]["channels"]
             if ch_data.get("id") == self._channel_id),  # Match by channel_id (PK)
            {} # Default to empty dict if not found
        )
        return {
            "manual_water_amount": channel_device_data.get("manual_water_amount", 0) # Default to 0 if not in dict
        }

    async def async_set_water_amount(self, amount: float) -> None:
        """Set the water amount for this channel."""
        if amount <= 0:
            _LOGGER.error("Invalid water amount %f for device %s channel ID %s (display index %s)", 
                        amount, self._device_id, self._channel_id, self._channel_display_index)
            return
            
        channel_device_data = next(
            (ch_data for ch_data in self.coordinator.data[self._device_id]["device"]["channels"]
             if ch_data.get("id") == self._channel_id), # Match by channel_id (PK)
            None # Default to None if not found
        )

        if channel_device_data is None:
            _LOGGER.error("Channel data not found for device %s channel ID %s to set water amount.",
                          self._device_id, self._channel_id)
            return
            
        channel_device_data["manual_water_amount"] = amount # Updates local coordinator copy
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        if not self.available:
            _LOGGER.error("Device %s is not available", self._device_id)
            return

        try:
            channel_device_data = next(
                (ch_data for ch_data in self.coordinator.data[self._device_id]["device"]["channels"]
                 if ch_data.get("id") == self._channel_id), # Match by channel_id (PK)
                {}
            )
            water_amount = channel_device_data.get("manual_water_amount", 0)
            
            if water_amount <= 0:
                _LOGGER.error("Invalid water amount %f for device %s channel ID %s (display index %s)", 
                            water_amount, self._device_id, self._channel_id, self._channel_display_index)
                return
                
            await self._api.trigger_watering(
                self._device_id,
                self._channel_id, # Use channel_id (PK) for the API call
                water_amount,
            )
            self._is_on = True
            self.async_write_ha_state()
        except Exception as error:
            _LOGGER.error("Failed to trigger watering: %s", error)
            self._is_on = False
            self.coordinator.data[self._device_id]["available"] = False
            self.async_write_ha_state()
            raise

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        self._is_on = False
        self.async_write_ha_state()
