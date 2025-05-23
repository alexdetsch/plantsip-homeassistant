"""Config flow for PlantSip integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import aiohttp # Add import for aiohttp

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
import homeassistant.helpers.config_validation as cv
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PlantSipAPI
from .const import (
    DOMAIN,
    DEFAULT_SERVER_URL,
    CONF_USE_DEFAULT_SERVER,
    CONF_API_KEY,
    CONF_AUTH_METHOD,
    AUTH_METHOD_API_KEY,
    AUTH_METHOD_CREDENTIALS,
)
from .exceptions import PlantSipAuthError, PlantSipConnectionError, PlantSipApiError

_LOGGER = logging.getLogger(__name__)


class PlantSipConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PlantSip."""

    VERSION = 1
    _config_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step: Host configuration."""
        errors = {}
        if user_input is not None:
            self._config_data[CONF_USE_DEFAULT_SERVER] = user_input[CONF_USE_DEFAULT_SERVER]
            if user_input[CONF_USE_DEFAULT_SERVER]:
                self._config_data[CONF_HOST] = DEFAULT_SERVER_URL
            else:
                self._config_data[CONF_HOST] = user_input[CONF_HOST].rstrip("/")
            
            # Test connectivity to host (basic check, not auth yet)
            try:
                session = async_get_clientsession(self.hass)
                async with session.get(f"{self._config_data[CONF_HOST]}/") as response: # Check root path or a known public path
                    if response.status >= 400 and response.status != 401 and response.status != 403 : # Allow auth errors, but not server errors
                         raise PlantSipConnectionError(f"Host test failed with status {response.status}")
            except (PlantSipConnectionError, aiohttp.ClientError) as e:
                _LOGGER.error("Failed to connect to host %s: %s", self._config_data[CONF_HOST], e)
                errors["base"] = "cannot_connect_host"
            
            if not errors:
                return await self.async_step_auth_method()

        current_use_default = self._config_data.get(CONF_USE_DEFAULT_SERVER, True)
        current_host = self._config_data.get(CONF_HOST, "") if not current_use_default else ""

        schema = {
            vol.Required(CONF_USE_DEFAULT_SERVER, default=current_use_default): bool,
        }
        if not current_use_default: # Only show host field if default is not used
             schema[vol.Required(CONF_HOST, default=current_host)] = str
        
        # Need to rebuild schema based on current selection for dynamic form
        # This is tricky with voluptuous. A common pattern is to show/hide in UI or use options flow.
        # For simplicity, if user_input is present, we use its value for CONF_USE_DEFAULT_SERVER.
        # If not, we use the default.
        
        # Simplified schema logic for initial display and re-display on error.
        # Determine current values for form fields based on user_input (if re-displaying)
        # or _config_data (if navigating back) or defaults (initial display).
        if user_input is not None:
            # Form is being re-displayed (e.g., after error or user interaction changing the checkbox)
            current_use_default_server = user_input.get(CONF_USE_DEFAULT_SERVER, True)
            current_host_value = user_input.get(CONF_HOST, "")
        else:
            # Initial display of the form, or navigating back.
            current_use_default_server = self._config_data.get(CONF_USE_DEFAULT_SERVER, True)
            if not current_use_default_server:
                current_host_value = self._config_data.get(CONF_HOST, "")
            else:
                current_host_value = "" # Host field not shown, so its default value for the input field is less critical

        # Build the schema dictionary for the form
        form_schema_dict = {
            vol.Required(CONF_USE_DEFAULT_SERVER, default=current_use_default_server): bool,
        }
        if not current_use_default_server:
            form_schema_dict[vol.Required(CONF_HOST, default=current_host_value)] = str
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(form_schema_dict),
            errors=errors,
            description_placeholders={"default_host": DEFAULT_SERVER_URL},
        )


    async def async_step_auth_method(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the auth method selection step."""
        if user_input is not None:
            self._config_data[CONF_AUTH_METHOD] = user_input[CONF_AUTH_METHOD]
            if user_input[CONF_AUTH_METHOD] == AUTH_METHOD_CREDENTIALS:
                return await self.async_step_credentials()
            return await self.async_step_api_key_input()

        return self.async_show_form(
            step_id="auth_method",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_AUTH_METHOD, default=AUTH_METHOD_CREDENTIALS
                    ): vol.In([AUTH_METHOD_CREDENTIALS, AUTH_METHOD_API_KEY]),
                }
            ),
        )

    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the credentials input step."""
        errors = {}
        if user_input is not None:
            api = PlantSipAPI(
                host=self._config_data[CONF_HOST],
                session=async_get_clientsession(self.hass),
            )
            try:
                api_key = await api.exchange_credentials_for_api_key(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
                self._config_data[CONF_API_KEY] = api_key
                
                # Test the obtained API key
                api_with_key = PlantSipAPI(
                    host=self._config_data[CONF_HOST],
                    session=async_get_clientsession(self.hass),
                    api_key=api_key
                )
                await api_with_key.test_api_key()

                return self.async_create_entry(
                    title="PlantSip", data=self._config_data
                )
            except PlantSipConnectionError:
                errors["base"] = "cannot_connect"
            except PlantSipAuthError:
                errors["base"] = "invalid_auth_credentials" # Specific error for credentials
            except PlantSipApiError as e:
                _LOGGER.error("API error during credential exchange: %s", e)
                errors["base"] = "api_error_credentials"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during credential exchange")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="credentials",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_api_key_input(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the API key input step."""
        errors = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            api = PlantSipAPI(
                host=self._config_data[CONF_HOST],
                session=async_get_clientsession(self.hass),
                api_key=api_key,
            )
            try:
                await api.test_api_key()
                self._config_data[CONF_API_KEY] = api_key
                return self.async_create_entry(
                    title="PlantSip", data=self._config_data
                )
            except PlantSipConnectionError:
                errors["base"] = "cannot_connect"
            except PlantSipAuthError: # This will be raised by test_api_key if key is bad
                errors["base"] = "invalid_api_key"
            except PlantSipApiError as e:
                _LOGGER.error("API error during API key test: %s", e)
                errors["base"] = "api_error_key_test"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during API key test")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="api_key_input",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )
