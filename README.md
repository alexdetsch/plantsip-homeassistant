# PlantSip Integration for Home Assistant

This custom integration allows you to monitor and control your PlantSip plant watering devices through Home Assistant.

## Features

- Monitor soil moisture levels for each plant
- Track water tank levels
- Monitor battery status (voltage, level, charging state)
- Control watering manually through switches
- Automatic status updates every 2 minutes

## Installation

### HACS (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Go to HACS > Integrations
3. Click on the three dots in the top right corner
4. Click "Custom repositories"
5. Add `alex-detsch/ha-plantsip` as a custom repository
6. Click "Install" on the PlantSip integration
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/plantsip` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "PlantSip"
4. Enter your PlantSip API host and access token

## Entities Created

For each PlantSip device, the following entities will be created:

### Sensors
- Soil moisture level for each channel (%)
- Water tank level (%)
- Battery voltage (V)
- Battery level (%)
- Power supply status (connected/disconnected)
- Battery charging status (charging/not charging)

### Switches
- Manual watering control for each channel

## Support

For bugs and feature requests, please [open an issue](https://github.com/alex-detsch/ha-plantsip/issues) on GitHub.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
