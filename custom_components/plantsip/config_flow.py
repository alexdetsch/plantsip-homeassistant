"""Config flow for PlantSip integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PlantSipAPI
from .const import DOMAIN
from .exceptions import PlantSipAuthError, PlantSipConnectionError

_LOGGER = logging.getLogger(__name__)

class PlantSipConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PlantSip."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                api = PlantSipAPI(
                    host=user_input[CONF_HOST],
                    access_token=user_input[CONF_ACCESS_TOKEN],
                    session=async_get_clientsession(self.hass),
                )
                
                # Test the credentials by making an API call
                await api.get_devices()

                return self.async_create_entry(
                    title="PlantSip",
                    data=user_input,
                )

            except PlantSipConnectionError:
                errors["base"] = "cannot_connect"
            except PlantSipAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_ACCESS_TOKEN): str,
                }
            ),
            errors=errors,
        )
