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
            device_summaries = await self.api.get_devices()
            _LOGGER.debug("Processing device summaries: %s", device_summaries)
            data = {}
            active_device_ids_from_api = {str(ds.get("device_id")) for ds in device_summaries if ds.get("device_id")}


            for device_summary_item in device_summaries:
                device_id = None # Initialize device_id here for broader scope in error handling
                try:
                    if not isinstance(device_summary_item, dict):
                        _LOGGER.error("Invalid device summary data format: %s", device_summary_item)
                        continue
                    
                    device_id = str(device_summary_item.get("device_id"))
                    if not device_id:
                        _LOGGER.error("Device summary missing device_id: %s", device_summary_item)
                        continue
                    
                    # Fetch full device details to get complete channel information
                    full_device_details = await self.api.get_device_details(device_id)
                    if not isinstance(full_device_details, dict):
                        _LOGGER.error("Invalid full device details format for %s: %s", device_id, full_device_details)
                        data[device_id] = { # Store minimal info to mark as unavailable
                            "device": {"device_id": device_id, "name": device_summary_item.get("name", device_id), "channels": []},
                            "status": {}, "available": False}
                        continue

                    status = await self.api.get_device_status(device_id)
                    
                    # Ensure channels exist and are properly formatted (from full_device_details)
                    channels_from_full_details = full_device_details.get("channels", [])
                    if not isinstance(channels_from_full_details, list):
                        _LOGGER.error("Invalid channels format in full details for device %s: %s", device_id, channels_from_full_details)
                        channels_from_full_details = []
                        
                    # Process each channel
                    processed_channels_data = []
                    for channel_api_data in channels_from_full_details: # Use channels from full details
                        if isinstance(channel_api_data, dict):
                            channel_id_pk = channel_api_data.get("id")
                            channel_idx_display = channel_api_data.get("channel_index")
                            
                            if channel_id_pk is not None and channel_idx_display is not None:
                                processed_channels_data.append(channel_api_data)
                            else:
                                # This error should ideally not happen now if full_device_details.channels is used
                                # and Channel schema guarantees 'id' and 'channel_index'.
                                _LOGGER.error(
                                    "Channel data from full details for device %s missing 'id' or 'channel_index': %s. This may indicate an API inconsistency.",
                                    device_id,
                                    channel_api_data,
                                )
                        else:
                            _LOGGER.error(
                                "Invalid channel format in full details for device %s: %s", device_id, channel_api_data
                            )
                    
                    # Update the 'channels' in the full_device_details object that will be stored.
                    full_device_details["channels"] = processed_channels_data
                    
                    data[device_id] = {
                        "device": full_device_details, # Store the full device details
                        "status": status,
                        "available": True
                    }
                except Exception as device_err:
                    _LOGGER.error("Error processing device %s: %s", device_id or device_summary_item.get("device_id", "unknown"), str(device_err), exc_info=True)
                    # Mark this specific device as unavailable if we have an ID for it
                    current_device_id_for_error = device_id or str(device_summary_item.get("device_id","unknown_device_at_error"))
                    data[current_device_id_for_error] = {
                        "device": {"device_id": current_device_id_for_error, "name": device_summary_item.get("name", current_device_id_for_error), "channels": []}, 
                        "status": {},
                        "available": False 
                    }
                    continue # Continue with the next device summary
            
            # Handle devices that were previously in coordinator.data but are no longer reported by the API
            if self.data: # Check if coordinator already has data
                previous_device_ids = set(self.data.keys())
                missing_device_ids = previous_device_ids - active_device_ids_from_api
                for missing_id in missing_device_ids:
                    if missing_id in self.data and self.data[missing_id].get("available", False):
                        _LOGGER.info("Device %s previously available, now missing from API response. Marking unavailable.", missing_id)
                        # Preserve existing device and status structure but mark as unavailable
                        data[missing_id] = self.data[missing_id].copy()
                        data[missing_id]["available"] = False
                    elif missing_id not in data : # If not already handled (e.g. by an error above)
                         data[missing_id] = {
                            "device": {"device_id": missing_id, "name": f"Device {missing_id} (removed)", "channels": []},
                            "status": {},
                            "available": False
                        }


            if not data and device_summaries: # If we had summaries but couldn't process any into 'data'
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
