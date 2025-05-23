"""Constants for the PlantSip integration."""
from datetime import timedelta

DOMAIN = "plantsip"
MANUFACTURER = "PlantSip"
SCAN_INTERVAL = timedelta(minutes=2)

# API Configuration
API_TIMEOUT = 30  # seconds
MAX_WATER_AMOUNT = 10000  # ml
MIN_WATER_AMOUNT = 1  # ml
DEFAULT_WATER_AMOUNT = 50.0  # ml

# Configuration
CONF_DEVICE_ID = "device_id"
CONF_USE_DEFAULT_SERVER = "use_default_server"
DEFAULT_SERVER_URL = "https://api.plantsip.de"

CONF_API_KEY = "api_key"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_AUTH_METHOD = "auth_method"

AUTH_METHOD_API_KEY = "api_key"
AUTH_METHOD_CREDENTIALS = "credentials"
API_KEY_NAME = "Home Assistant Integration"

# Error handling
MAX_CONSECUTIVE_FAILURES = 3
RETRY_DELAY = timedelta(seconds=30)
