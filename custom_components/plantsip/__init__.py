"""The PlantSip integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_HOST,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PlantSipAPI
from .const import DOMAIN, SCAN_INTERVAL

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
        access_token=entry.data[CONF_ACCESS_TOKEN],
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

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            devices = await self.api.get_devices()
            data = {}
            for device in devices:
                device_id = device["device_id"]
                status = await self.api.get_device_status(device_id)
                data[device_id] = {
                    "device": device,
                    "status": status
                }
            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
