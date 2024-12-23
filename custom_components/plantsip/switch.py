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
        for channel in device_data["device"]["channels"]:
            entities.append(
                PlantSipWateringSwitch(
                    coordinator,
                    api,
                    device_id,
                    channel["channel_index"],
                    channel["manual_water_amount"],
                )
            )
    
    async_add_entities(entities)

class PlantSipWateringSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a watering switch."""

    def __init__(self, coordinator, api, device_id, channel_index, water_amount):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._api = api
        self._device_id = device_id
        self._channel_index = channel_index
        self._water_amount = water_amount
        self._is_on = False
        
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

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        try:
            await self._api.trigger_watering(
                self._device_id,
                self._channel_index,
                self._water_amount,
            )
            self._is_on = True
            self.async_write_ha_state()
        except Exception as error:
            _LOGGER.error("Failed to trigger watering: %s", error)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        self._is_on = False
        self.async_write_ha_state()
