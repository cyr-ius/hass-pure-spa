"""Config flow for the Pure spa integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import probatio
from espspapy import (
    PairingError,
    Spa,
    SpaException,
    SpaInfo,
    async_discover,
    async_pair,
)
from espspapy.helpers import parse_bssid
from homeassistant.components.network import async_get_source_ip
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_PASSWORD
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_BSSID,
    CONF_LOCAL_IP,
    CONF_SSID,
    CONF_UID,
    DOMAIN,
    IDENTIFY_RETRIES,
    IDENTIFY_RETRY_DELAY,
)

_LOGGER = logging.getLogger(__name__)

TITLE = "Pure spa"

PAIR_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_SSID): str,
        probatio.Optional(CONF_BSSID): str,
        probatio.Optional(CONF_PASSWORD, default=""): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        probatio.Required(CONF_LOCAL_IP): str,
    }
)


async def async_identify(host: str, retries: int = 1) -> SpaInfo:
    """Return the spa identity, retrying while its TCP server starts."""
    spa = Spa(
        host,
        timeout=10.0,
        retries=retries,
        retry_delay=IDENTIFY_RETRY_DELAY,
        heartbeat_interval=None,
    )
    try:
        return await spa.async_identify()
    finally:
        await spa.async_close()


class PureSpaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pure spas."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._discovered: dict[str, SpaInfo] = {}
        self._pair_input: dict[str, Any] = {}
        self._pair_task: asyncio.Task[tuple[str, str, SpaInfo]] | None = None
        self._paired: tuple[str, str, SpaInfo] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose how to add the spa."""
        return self.async_show_menu(
            step_id="user", menu_options=["discover", "manual", "pair"]
        )

    async def _async_create(
        self, host: str, gateway: SpaInfo, mac: str | None = None
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(gateway.uid)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        return self.async_create_entry(
            title=TITLE,
            data={CONF_HOST: host, CONF_UID: gateway.uid, CONF_MAC: mac},
        )

    async def async_step_discover(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Find the spas of the LAN."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            try:
                gateway = await async_identify(host, retries=3)
            except SpaException:
                errors["base"] = "cannot_connect"
            else:
                return await self._async_create(host, gateway)
        else:
            try:
                found = await async_discover()
            except OSError as err:
                _LOGGER.debug("Discovery failed: %s", err)
                found = []
            configured = self._async_current_ids(include_ignore=False)
            self._discovered = {
                gateway.ip: gateway
                for gateway in found
                if gateway.ip and gateway.uid not in configured
            }
            if not self._discovered:
                return self.async_abort(reason="no_devices_found")

        options = [
            SelectOptionDict(value=ip, label=f"{gateway.uid} ({ip})")
            for ip, gateway in self._discovered.items()
        ]
        return self.async_show_form(
            step_id="discover",
            data_schema=probatio.Schema(
                {
                    probatio.Required(CONF_HOST): SelectSelector(
                        SelectSelectorConfig(options=options)
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a spa already connected to the Wi-Fi."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            try:
                gateway = await async_identify(host, retries=3)
            except SpaException:
                errors["base"] = "cannot_connect"
            else:
                return await self._async_create(host, gateway)

        return self.async_show_form(
            step_id="manual",
            data_schema=self.add_suggested_values_to_schema(
                probatio.Schema({probatio.Required(CONF_HOST): str}), user_input
            ),
            errors=errors,
        )

    async def async_step_pair(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Send the Wi-Fi credentials to the spa (ESP-Touch)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                if bssid := user_input.get(CONF_BSSID):
                    parse_bssid(bssid)
            except ValueError:
                errors[CONF_BSSID] = "invalid_bssid"
            else:
                self._pair_input = user_input
                self._pair_task = None
                return await self.async_step_pair_progress()

        suggested = user_input or {
            CONF_LOCAL_IP: await async_get_source_ip(self.hass),
            **{k: v for k, v in self._pair_input.items() if k != CONF_PASSWORD},
        }
        return self.async_show_form(
            step_id="pair",
            data_schema=self.add_suggested_values_to_schema(PAIR_SCHEMA, suggested),
            errors=errors,
        )

    async def _async_pair(self) -> tuple[str, str, SpaInfo]:
        data = self._pair_input
        try:
            result = await async_pair(
                data[CONF_SSID],
                data.get(CONF_PASSWORD, ""),
                data[CONF_LOCAL_IP],
                bssid=data.get(CONF_BSSID) or None,
            )
        except (OSError, ValueError) as err:
            raise PairingError(str(err)) from err
        _LOGGER.debug(
            "Spa module %s joined the Wi-Fi with IP %s", result.mac, result.ip
        )
        try:
            gateway = await async_identify(result.ip, retries=IDENTIFY_RETRIES)
        except SpaException as err:
            raise PairingError(str(err)) from err
        return result.ip, result.mac, gateway

    async def async_step_pair_progress(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Wait for the spa to join the Wi-Fi."""
        if self._pair_task is None:
            self._pair_task = self.hass.async_create_task(self._async_pair())
        if not self._pair_task.done():
            return self.async_show_progress(
                step_id="pair_progress",
                progress_action="pairing",
                progress_task=self._pair_task,
            )
        try:
            self._paired = self._pair_task.result()
        except PairingError as err:
            _LOGGER.warning("Pairing failed: %s", err)
            return self.async_show_progress_done(next_step_id="pair_failed")
        finally:
            self._pair_task = None
        return self.async_show_progress_done(next_step_id="pair_finish")

    async def async_step_pair_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pairing failed: show the form again."""
        return self.async_show_form(
            step_id="pair",
            data_schema=self.add_suggested_values_to_schema(
                PAIR_SCHEMA,
                {k: v for k, v in self._pair_input.items() if k != CONF_PASSWORD},
            ),
            errors={"base": "pairing_failed"},
        )

    async def async_step_pair_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the entry of the paired spa."""
        assert self._paired is not None
        host, mac, gateway = self._paired
        return await self._async_create(host, gateway, mac)
