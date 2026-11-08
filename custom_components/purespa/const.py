"""Constants for the Pure spa integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "purespa"

PLATFORMS = [Platform.CLIMATE, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]

CONF_UID = "uid"
CONF_SSID = "ssid"
CONF_BSSID = "bssid"
CONF_LOCAL_IP = "local_ip"

SCAN_INTERVAL = timedelta(seconds=30)
HEARTBEAT_INTERVAL = timedelta(seconds=50)

IDENTIFY_RETRIES = 10
IDENTIFY_RETRY_DELAY = 2.0
