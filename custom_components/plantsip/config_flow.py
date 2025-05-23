"""Config flow for PlantSip integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
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
        errors: dict[str, str] = {}

        if user_input is not None:
            submitted_use_default = user_input[CONF_USE_DEFAULT_SERVER]
            self._config_data[CONF_USE_DEFAULT_SERVER] = submitted_use_default

            final_host: str | None = None
            if submitted_use_default:
                final_host = DEFAULT_SERVER_URL
                self._config_data[CONF_HOST] = final_host
            else:  # Not using default server
                submitted_host_value = user_input.get(CONF_HOST)
                if not submitted_host_value:  # Covers None or empty string
                    errors[CONF_HOST] = "custom_host_required"
                else:
                    final_host = submitted_host_value.rstrip("/")
                    self._config_data[CONF_HOST] = final_host
            
            if final_host and not errors:  # Only test connection if host is determined and no prior errors
                try:
                    session = async_get_clientsession(self.hass)
                    timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout for initial test
                    async with session.get(f"{final_host}/", timeout=timeout) as response:
                        if response.status >= 500:
                            raise PlantSipConnectionError(f"Server error: status {response.status}")
                        elif response.status >= 400 and response.status not in (401, 403, 404):
                            raise PlantSipConnectionError(f"Host test failed with status {response.status}")
                        # 401, 403, 404 are acceptable as they indicate the server is responding
                        _LOGGER.debug("Host %s responded with status %d", final_host, response.status)
                except asyncio.TimeoutError as e:
                    _LOGGER.error("Timeout connecting to host %s: %s", final_host, e)
                    if not submitted_use_default:
                        errors[CONF_HOST] = "timeout_connect_host"
                    else:
                        errors["base"] = "timeout_connect_host"
                except (PlantSipConnectionError, aiohttp.ClientError) as e:
                    _LOGGER.error("Failed to connect to host %s: %s", final_host, e)
                    # Associate error with host field if it was user-provided, else base
                    if not submitted_use_default:
                        errors[CONF_HOST] = "cannot_connect_host"
                    else:
                        errors["base"] = "cannot_connect_host" # Default server connection failed
            
            if not errors:
                return await self.async_step_auth_method()

        # Schema generation for re-displaying the form
        # Determine current values for form fields for schema generation.
        # If user_input is present, it means we are re-displaying the form (e.g. after an error).
        # Use values from user_input to pre-fill the form.
        # Otherwise (initial display), use values from _config_data (if navigating back) or defaults.
        if user_input:
            current_use_default_server_for_schema = user_input.get(CONF_USE_DEFAULT_SERVER, True)
            current_host_for_schema_default = user_input.get(CONF_HOST, "")
        else:
            current_use_default_server_for_schema = self._config_data.get(CONF_USE_DEFAULT_SERVER, True)
            current_host_for_schema_default = self._config_data.get(CONF_HOST, "") if not current_use_default_server_for_schema else ""

        # Build the schema dictionary for the form
        form_schema_dict = {
            vol.Required(CONF_USE_DEFAULT_SERVER, default=current_use_default_server_for_schema): bool,
        }
        if not current_use_default_server_for_schema:
            form_schema_dict[vol.Required(CONF_HOST, default=current_host_for_schema_default)] = str
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(form_schema_dict),
            errors=errors, # Pass any errors to the form
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
                timeout=30  # 30 second timeout for auth operations
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
                    api_key=api_key,
                    timeout=30
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
            api_key = user_input[CONF_API_KEY].strip()
            if not api_key:
                errors[CONF_API_KEY] = "empty_api_key"
            else:
                api = PlantSipAPI(
                    host=self._config_data[CONF_HOST],
                    session=async_get_clientsession(self.hass),
                    api_key=api_key,
                    timeout=30
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
                    errors[CONF_API_KEY] = "invalid_api_key"
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
