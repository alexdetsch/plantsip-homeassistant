"""The PlantSip integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PlantSipAPI
from .const import DOMAIN, SCAN_INTERVAL, CONF_API_KEY # Import CONF_API_KEY
from .exceptions import PlantSipError

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PlantSip from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    api = PlantSipAPI(
        host=entry.data[CONF_HOST],
        api_key=entry.data[CONF_API_KEY], # Use CONF_API_KEY
        session=async_get_clientsession(hass),
    )

    coordinator = PlantSipDataUpdateCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

class PlantSipDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching PlantSip data."""

    def __init__(self, hass: HomeAssistant, api: PlantSipAPI) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api
        self.last_update_success = True

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            devices = await self.api.get_devices()
            _LOGGER.debug("Processing devices: %s", devices)
            data = {}
            for device in devices:
                try:
                    if not isinstance(device, dict):
                        _LOGGER.error("Invalid device data format: %s", device)
                        continue
                    
                    device_id = str(device.get("device_id"))
                    if not device_id:
                        _LOGGER.error("Device missing device_id: %s", device)
                        continue
                        
                    status = await self.api.get_device_status(device_id)
                    
                    # Ensure channels exist and are properly formatted
                    channels = device.get("channels", [])
                    if not isinstance(channels, list):
                        _LOGGER.error("Invalid channels format for device %s: %s", device_id, channels)
                        channels = []
                        
                    # Process each channel
                    processed_channels_data = []
                    for channel_api_data in channels:
                        if isinstance(channel_api_data, dict):
                            channel_id_pk = channel_api_data.get("id")
                            channel_idx_display = channel_api_data.get("channel_index")
                            
                            if channel_id_pk is not None and channel_idx_display is not None:
                                # We store the original channel dict from the API if it contains
                                # 'id' and 'channel_index'. Other fields like 'manual_water_amount'
                                # are assumed to be in this dict if needed by entities.
                                processed_channels_data.append(channel_api_data)
                            else:
                                _LOGGER.error(
                                    "Channel data for device %s missing 'id' or 'channel_index': %s",
                                    device_id,
                                    channel_api_data,
                                )
                        else:
                            _LOGGER.error(
                                "Invalid channel format in device %s: %s", device_id, channel_api_data
                            )
                    
                    # Update device data with processed channels
                    device["channels"] = processed_channels_data
                    
                    data[device_id] = {
                        "device": device,
                        "status": status,
                        "available": True
                    }
                except Exception as device_err:
                    _LOGGER.error("Error fetching status for device %s: %s", device.get("device_id", "unknown"), str(device_err))
                    continue
            
            if not data:
                self.last_update_success = False
                raise UpdateFailed("No device data could be fetched")
                
            self.last_update_success = True
            return data
            
        except PlantSipError as err:
            self.last_update_success = False
            _LOGGER.error("PlantSip API error: %s", str(err))
            raise UpdateFailed(f"Error communicating with PlantSip API: {err}")
        except Exception as err:
            self.last_update_success = False
            _LOGGER.error("Unexpected error in PlantSip update: %s", str(err), exc_info=True)
            raise UpdateFailed(f"Unexpected error: {err}")
