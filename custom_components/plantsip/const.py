"""Constants for the PlantSip integration."""
from datetime import timedelta

DOMAIN = "plantsip"
MANUFACTURER = "PlantSip"
SCAN_INTERVAL = timedelta(minutes=2)

# Configuration
CONF_DEVICE_ID = "device_id"
CONF_USE_DEFAULT_SERVER = "use_default_server"
DEFAULT_SERVER_URL = "https://api.plantsip.de"
