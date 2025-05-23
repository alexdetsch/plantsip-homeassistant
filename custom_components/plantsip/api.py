"""API client for PlantSip."""
import asyncio
import logging
from typing import Any, Dict, List

import aiohttp
from aiohttp import ClientError

from .exceptions import (
    PlantSipApiError,
    PlantSipAuthError,
    PlantSipConnectionError,
)
from .const import API_KEY_NAME

_LOGGER = logging.getLogger(__name__)

class PlantSipAPI:
    """API client for PlantSip."""

    def __init__(self, host: str, session: aiohttp.ClientSession, api_key: str | None = None) -> None:
        """Initialize the API client."""
        self._host = host.rstrip("/")
        self._api_key = api_key
        self._session = session

    async def _request(self, method: str, path: str, headers_override: dict | None = None, **kwargs) -> Any:
        """Make a request to the API."""
        headers = {}
        if headers_override:
            headers.update(headers_override)
        elif self._api_key:
            headers["X-API-Key"] = self._api_key  # Standard header for API keys
        
        headers.setdefault("Content-Type", "application/json")

        url = f"{self._host}{path}"

        _LOGGER.debug("Requesting %s %s with headers %s and data %s", method, url, {k: (v[:10] + "..." if k == "X-API-Key" else v) for k,v in headers.items()}, kwargs.get("json"))


        try:
            async with self._session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                _LOGGER.debug("Response status: %s, body: %s", response.status, await response.text() if response.content else "No content")
                if response.status == 401:
                    raise PlantSipAuthError("Invalid authentication credentials")
                if response.status == 403: # Forbidden, often due to bad API key or insufficient perms
                    raise PlantSipAuthError("Forbidden. Check API key permissions or validity.")
                if response.status >= 400:
                    error_detail = await response.text()
                    raise PlantSipApiError(
                        f"API request failed with status {response.status}: {error_detail}"
                    )
                if response.content_type == "application/json":
                    return await response.json()
                return await response.text() # For non-json responses like firmware update

        except ClientError as err:
            raise PlantSipConnectionError(f"Failed to connect to PlantSip API: {err}") from err
        except asyncio.TimeoutError as err:
            raise PlantSipConnectionError("Timeout while connecting to PlantSip API") from err

    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get all devices."""
        if not self._api_key:
            raise PlantSipAuthError("API key not set for get_devices request.")
        response = await self._request("GET", "/devices/") # Added trailing slash based on openapi
        _LOGGER.debug("Got devices response: %s", response)
        
        # Handle different response formats
        if isinstance(response, dict) and "items" in response:
            devices = response.get("items", [])
            if not isinstance(devices, list):
                raise PlantSipApiError(f"Invalid devices data format: expected list in 'items', got {type(devices)}")
            return devices
        elif isinstance(response, list):
            # Fallback for non-paginated list, though OpenAPI implies pagination
            _LOGGER.warning("Received direct list of devices, expected paginated response with 'items' key.")
            return response
        else:
            raise PlantSipApiError(f"Unexpected response format for devices: {type(response)}, content: {response}")

    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get status of a specific device."""
        if not self._api_key:
            raise PlantSipAuthError("API key not set for get_device_status request.")
        return await self._request("GET", f"/device/{device_id}/status/latest")

    async def trigger_watering(self, device_id: str, channel_id: int, water_amount: float) -> None:
        """Trigger manual watering for a specific channel."""
        if not self._api_key:
            raise PlantSipAuthError("API key not set for trigger_watering request.")
        await self._request(
            "POST",
            f"/device/{device_id}/channel/{channel_id}/water",
            json={"water_amount": water_amount},
        )

    async def exchange_credentials_for_api_key(self, username: str, password: str) -> str:
        """Login with username/password to get a short-lived token, then create and return a long-lived API key."""
        # Step 1: Get short-lived Bearer token
        token_url = f"{self._host}/token"
        login_data = {"username": username, "password": password}
        _LOGGER.debug("Attempting to get short-lived token from %s", token_url)
        try:
            async with self._session.post(token_url, json=login_data) as response:
                if response.status in (401, 422): # 422 for validation error (e.g. wrong body)
                    error_text = await response.text()
                    _LOGGER.error("Auth error getting token (%s): %s", response.status, error_text)
                    raise PlantSipAuthError(f"Invalid username or password. Server response: {error_text}")
                if response.status >= 400:
                    error_text = await response.text()
                    _LOGGER.error("API error getting token (%s): %s", response.status, error_text)
                    raise PlantSipApiError(f"Failed to get token: {response.status} - {error_text}")
                token_data = await response.json()
        except ClientError as err:
            _LOGGER.error("Connection error getting token: %s", err)
            raise PlantSipConnectionError(f"Connection error during token exchange: {err}")

        bearer_token = token_data.get("access_token")
        if not bearer_token:
            _LOGGER.error("No access_token in token response: %s", token_data)
            raise PlantSipApiError("No access_token received in token response.")
        _LOGGER.debug("Successfully obtained short-lived token.")

        # Step 2: Use Bearer token to create a long-lived API key
        api_key_creation_data = {"name": API_KEY_NAME} # Name for the API key
        auth_headers = {"Authorization": f"Bearer {bearer_token}"}
        
        _LOGGER.debug("Attempting to create long-lived API key.")
        created_key_data = await self._request(
            "POST",
            "/api-keys/", # Added trailing slash based on openapi
            headers_override=auth_headers,
            json=api_key_creation_data,
        )

        long_lived_api_key = created_key_data.get("api_key")
        if not long_lived_api_key:
            _LOGGER.error("No api_key in create API key response: %s", created_key_data)
            raise PlantSipApiError("No api_key received in create API key response.")
        _LOGGER.debug("Successfully created and obtained long-lived API key.")
        return long_lived_api_key

    async def test_api_key(self) -> None:
        """Tests the currently set API key by trying to fetch devices."""
        if not self._api_key:
            raise PlantSipAuthError("API key not set for testing.")
        _LOGGER.debug("Testing API key by fetching devices.")
        await self.get_devices()
        _LOGGER.debug("API key test successful.")
