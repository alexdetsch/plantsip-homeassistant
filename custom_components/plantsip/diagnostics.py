"""Diagnostics support for PlantSip."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD # Import from HA const
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_API_KEY # Import local const

TO_REDACT = {CONF_API_KEY, CONF_USERNAME, CONF_PASSWORD} # Add new keys

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Redact sensitive data from the diagnostics
    diagnostics_data = {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "data": coordinator.data,
    }

    return diagnostics_data
