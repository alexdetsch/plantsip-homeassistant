"""Config flow for PlantSip integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST
import homeassistant.helpers.config_validation as cv
from .const import DEFAULT_SERVER_URL, CONF_USE_DEFAULT_SERVER
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
                host = DEFAULT_SERVER_URL if user_input[CONF_USE_DEFAULT_SERVER] else user_input[CONF_HOST]
                api = PlantSipAPI(
                    host=host,
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

        if user_input is None:
            user_input = {}

        data_schema = {
            vol.Required(
                CONF_USE_DEFAULT_SERVER,
                default=user_input.get(CONF_USE_DEFAULT_SERVER, True),
            ): bool,
            vol.Required(CONF_ACCESS_TOKEN): str,
        }

        if not user_input.get(CONF_USE_DEFAULT_SERVER, True):
            data_schema[vol.Required(CONF_HOST, default="")] = str

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )
