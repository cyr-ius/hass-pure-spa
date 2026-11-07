# Pure Spa for Home Assistant

Control your PureSpa from Home Assistant, directly on your home network,
without the manufacturer app or cloud.

The official **Intex Link Spa Management** app is deprecated and no longer works.
This integration lets you keep using your connected spa, and even connect it
to your Wi-Fi, without it.

> [!IMPORTANT]
> This integration only works with **Intex PureSpa models released before
> 2024**, those using the **Intex Link Spa Management** app.
> Newer models are not supported.

## What it does

Once installed, your spa appears in Home Assistant and you can:

- **Heat the water**: turn the heater on or off and set the target
  temperature, while watching the current water temperature.
- **Turn on and off**: the spa, the filtration, the bubbles, the jets and the
  sanitizer.
- **Monitor**: the water temperature, the remaining time of the filtration,
  heating and sanitizer timers, and any error shown on the spa (low water flow,
  temperature too high, etc.), with a clear description.

Everything can be used in your dashboards, automations and scripts, for example
to start heating a few hours before you get in, or to be notified when the spa
reports an error.

## Pairing your spa

The official app, which used to connect the spa to the Wi-Fi, no longer works.
Home Assistant now does it itself.

When adding the integration, three choices are offered:

- **Connect a new spa to the Wi-Fi**: put the spa in Wi-Fi pairing mode, then
  enter your Wi-Fi name, password and the address (BSSID) of the access point
  closest to the spa. Home Assistant sends these settings to the spa and adds
  it automatically.
- **Search for spas on the local network**: for a spa already connected to the
  Wi-Fi.
- **Enter the IP address** of a spa already connected to the Wi-Fi.

Good to know:

- The spa only supports **2.4 GHz** Wi-Fi.
- Home Assistant must be on the same network as the spa. With Docker, use the
  host network mode (`network_mode: host`); Home Assistant OS needs nothing.
- Reserve the spa IP address in your router so it does not change.

## Installation

### With HACS

1. Add this repository to HACS as a custom repository (type *Integration*).
2. Install **Pure Spa**, then restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration** and search for
   **Pure Spa**.

### Manually

Copy the `custom_components/purespa` folder into the `custom_components`
folder of your Home Assistant configuration, restart, then add the **Pure Spa**
integration.

## Issues

Report problems on the
[issue tracker](https://github.com/cyr-ius/hass-pure-spa/issues).
