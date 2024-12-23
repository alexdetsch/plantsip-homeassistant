"""Binary sensor platform for PlantSip."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PlantSip binary sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = []
    for device_id, device_data in coordinator.data.items():
        if device_data.get("available", False):
            entities.extend((
                PlantSipPowerSupplyBinarySensor(coordinator, device_id),
                PlantSipBatteryChargingBinarySensor(coordinator, device_id),
            ))
    
    async_add_entities(entities)

class PlantSipPowerSupplyBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for power supply status."""

    def __init__(self, coordinator, device_id):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_device_class = BinarySensorDeviceClass.PLUG
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        
        device_data = coordinator.data[device_id]["device"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_data["name"],
            manufacturer=MANUFACTURER,
            model="PlantSip Device",
            sw_version=coordinator.data[device_id]["status"]["firmware_version"],
        )
        
    @property
    def unique_id(self):
        """Return unique ID for the binary sensor."""
        return f"{self._device_id}_power_supply"
        
    @property
    def name(self):
        """Return the name of the binary sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} {self.translation_key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "power_supply"

    @property
    def is_on(self):
        """Return true if power supply is connected."""
        return self.coordinator.data[self._device_id]["status"]["power_supply_connected"]

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._device_id in self.coordinator.data
            and self.coordinator.data[self._device_id].get("available", False)
        )

class PlantSipBatteryChargingBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for battery charging status."""

    def __init__(self, coordinator, device_id):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        
        device_data = coordinator.data[device_id]["device"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_data["name"],
            manufacturer=MANUFACTURER,
            model="PlantSip Device",
            sw_version=coordinator.data[device_id]["status"]["firmware_version"],
        )
        
    @property
    def unique_id(self):
        """Return unique ID for the binary sensor."""
        return f"{self._device_id}_battery_charging"
        
    @property
    def name(self):
        """Return the name of the binary sensor."""
        device_name = self.coordinator.data[self._device_id]["device"]["name"]
        return f"{device_name} {self.translation_key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "battery_charging"

    @property
    def is_on(self):
        """Return true if battery is charging."""
        return self.coordinator.data[self._device_id]["status"]["battery_charging"]

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._device_id in self.coordinator.data
            and self.coordinator.data[self._device_id].get("available", False)
        )
