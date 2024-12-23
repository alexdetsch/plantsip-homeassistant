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
        
        for channel in channels:
            channel_index = channel.get("channel_index")
            if channel_index is not None:
                entities.append(
                    PlantSipWateringSwitch(
                        coordinator,
                        api,
                        device_id,
                        channel_index,
                    )
                )
    
    async_add_entities(entities)

class PlantSipWateringSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a watering switch."""

    def __init__(self, coordinator, api, device_id, channel_index):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._api = api
        self._device_id = device_id
        self._channel_index = channel_index
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
        return f"{self._device_id}_watering_{self._channel_index}"
        
    @property
    def name(self):
        """Return the name of the switch."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} Channel {self._channel_index} {self.translation_key}"

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
            
        channel_data = next(
            (ch for ch in self.coordinator.data[self._device_id]["device"]["channels"] 
             if ch.get("channel_index") == self._channel_index),
            {}
        )
        return {
            "manual_water_amount": channel_data.get("manual_water_amount", 0)
        }

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        if not self.available:
            _LOGGER.error("Device %s is not available", self._device_id)
            return

        try:
            channel_data = next(
                (ch for ch in self.coordinator.data[self._device_id]["device"]["channels"] 
                 if ch.get("channel_index") == self._channel_index),
                {}
            )
            water_amount = channel_data.get("manual_water_amount", 0)
            
            if water_amount <= 0:
                _LOGGER.error("Invalid water amount for device %s channel %s", 
                            self._device_id, self._channel_index)
                return
                
            await self._api.trigger_watering(
                self._device_id,
                self._channel_index,
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
