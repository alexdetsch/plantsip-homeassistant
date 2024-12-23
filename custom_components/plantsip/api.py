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

_LOGGER = logging.getLogger(__name__)

class PlantSipAPI:
    """API client for PlantSip."""

    def __init__(self, host: str, access_token: str, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self._host = host.rstrip("/")
        self._access_token = access_token
        self._session = session

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        """Make a request to the API."""
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"{self._host}/v1{path}"
        
        try:
            async with self._session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                if response.status == 401:
                    raise PlantSipAuthError("Invalid authentication credentials")
                if response.status >= 400:
                    error_detail = await response.text()
                    raise PlantSipApiError(
                        f"API request failed with status {response.status}: {error_detail}"
                    )
                return await response.json()
                
        except ClientError as err:
            raise PlantSipConnectionError(f"Failed to connect to PlantSip API: {err}") from err
        except asyncio.TimeoutError as err:
            raise PlantSipConnectionError("Timeout while connecting to PlantSip API") from err

    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get all devices."""
        return await self._request("GET", "/devices")

    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get status of a specific device."""
        return await self._request("GET", f"/device/{device_id}/status/latest")

    async def trigger_watering(self, device_id: str, channel_id: int, water_amount: float) -> None:
        """Trigger manual watering for a specific channel."""
        await self._request(
            "POST",
            f"/device/{device_id}/channel/{channel_id}/water",
            json={"water_amount": water_amount},
        )
