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
  heating and sanitizer timers, the delayed heater start set on the spa, and
  any error shown on the spa (low water flow, temperature too high, etc.), with
  a clear description.
- **Schedule**: run the filtration, the heater or the sanitizer for 1 to 48
  hours, now or after a delay, with the **Set timer** action, and cancel it
  with **Clear timer**. The heater can use its own target temperature.

Everything can be used in your dashboards, automations and scripts, for example
to start heating a few hours before you get in, or to be notified when the spa
reports an error.

### Timers

```yaml
action: purespa.set_timer
data:
  config_entry_id: <your spa>
  device: heater
  hours: 3
  delay:
    hours: 2
  temperature: 38
```

A new timer replaces the previous one of the same device.

Good to know, because of what the spa reports:

- The spa does not report a timer set from Home Assistant before it starts.
  Home Assistant remembers it and shows it in the `scheduled_start` and
  `scheduled_end` attributes of the timer sensor, until it restarts.
- The control panel only offers some durations (filtration 2, 4 or 6 hours,
  sanitizer 3, 5 or 8 hours). The actions accept any duration from 1 to 48
  hours, but other durations were not tried on a spa yet.
- During the last hour of a timer or of a delayed start, the spa does not
  report the remaining time: the sensor is unknown.
- The heater activity is unknown when the water is at the target temperature:
  the spa may still heat, for up to about an hour, or not.

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

1. Add this repository to HACS as a custom repository (type _Integration_).
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
