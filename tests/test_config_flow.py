"""Tests for the Pure spa config flow."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from espspapy import PairingResult, SpaConnectionError, SpaInfo
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.purespa.config_flow import async_identify
from custom_components.purespa.const import (
    CONF_BSSID,
    CONF_LOCAL_IP,
    CONF_SSID,
    CONF_UID,
    DOMAIN,
)

from .conftest import HOST, MAC, UID

pytestmark = pytest.mark.usefixtures("mock_setup_entry")

PAIR_INPUT = {
    CONF_SSID: "MyWifi",
    CONF_BSSID: "11:22:33:44:55:66",
    CONF_PASSWORD: "secret",
    CONF_LOCAL_IP: "192.168.1.10",
}


async def _start(hass: HomeAssistant, step: str):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": step}
    )


async def test_identify() -> None:
    """Test the identification helper closes the client."""
    with patch("custom_components.purespa.config_flow.Spa", autospec=True) as spa:
        spa.return_value.async_identify.return_value = SpaInfo(uid=UID)
        assert (await async_identify(HOST)).uid == UID
    spa.return_value.async_close.assert_awaited_once()


async def test_manual(hass: HomeAssistant, mock_identify: AsyncMock) -> None:
    """Test the manual step, with a connection error first."""
    result = await _start(hass, "manual")
    assert result["type"] is FlowResultType.FORM

    mock_identify.side_effect = SpaConnectionError("boom")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["errors"] == {"base": "cannot_connect"}

    mock_identify.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HOST: HOST, CONF_UID: UID, CONF_MAC: None}
    assert result["result"].unique_id == UID


async def test_manual_already_configured(
    hass: HomeAssistant, mock_identify: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test an already configured spa updates its host."""
    mock_config_entry.add_to_hass(hass)
    result = await _start(hass, "manual")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.1.99"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.data[CONF_HOST] == "192.168.1.99"


async def test_discover(hass: HomeAssistant, mock_identify: AsyncMock) -> None:
    """Test the discovery step."""
    with patch(
        "custom_components.purespa.config_flow.async_discover",
        return_value=[SpaInfo(uid=UID, ip=HOST), SpaInfo(uid="noip")],
    ):
        result = await _start(hass, "discover")
    assert result["type"] is FlowResultType.FORM

    mock_identify.side_effect = SpaConnectionError("boom")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["errors"] == {"base": "cannot_connect"}

    mock_identify.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_discover_nothing(hass: HomeAssistant) -> None:
    """Test the discovery aborts when no spa is found."""
    with patch(
        "custom_components.purespa.config_flow.async_discover",
        side_effect=OSError("no network"),
    ):
        result = await _start(hass, "discover")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


@pytest.fixture
def mock_pair_env() -> MagicMock:
    """Mock the network helpers of the pair step."""
    with (
        patch(
            "custom_components.purespa.config_flow.async_get_source_ip",
            return_value="192.168.1.10",
        ),
        patch(
            "custom_components.purespa.config_flow.get_current_bssid",
            return_value="11:22:33:44:55:66",
        ),
        patch("custom_components.purespa.config_flow.async_pair") as pair,
    ):
        yield pair


async def _pair(hass: HomeAssistant, user_input: dict):
    result = await _start(hass, "pair")
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "pair"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )
    while result["type"] in (
        FlowResultType.SHOW_PROGRESS,
        FlowResultType.SHOW_PROGRESS_DONE,
    ):
        await hass.async_block_till_done()
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
    return result


async def test_pair(
    hass: HomeAssistant, mock_pair_env: MagicMock, mock_identify: AsyncMock
) -> None:
    """Test a successful ESP-Touch pairing."""
    mock_pair_env.return_value = PairingResult(mac=MAC, ip=HOST)
    result = await _pair(hass, PAIR_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HOST: HOST, CONF_UID: UID, CONF_MAC: MAC}
    mock_pair_env.assert_awaited_once_with(
        "MyWifi", "secret", "192.168.1.10", bssid="11:22:33:44:55:66"
    )


async def test_pair_invalid_bssid(
    hass: HomeAssistant, mock_pair_env: MagicMock
) -> None:
    """Test an invalid BSSID is rejected."""
    result = await _pair(hass, {**PAIR_INPUT, CONF_BSSID: "nope"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_BSSID: "invalid_bssid"}


@pytest.mark.parametrize(
    ("pair_error", "identify_error"),
    [(OSError("no socket"), None), (None, SpaConnectionError("boom"))],
)
async def test_pair_failed(
    hass: HomeAssistant,
    mock_pair_env: MagicMock,
    mock_identify: AsyncMock,
    pair_error: Exception | None,
    identify_error: Exception | None,
) -> None:
    """Test a failed pairing shows the form again."""
    mock_pair_env.return_value = PairingResult(mac=MAC, ip=HOST)
    mock_pair_env.side_effect = pair_error
    mock_identify.side_effect = identify_error
    result = await _pair(hass, PAIR_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "pair"
    assert result["errors"] == {"base": "pairing_failed"}


async def test_pair_in_progress(
    hass: HomeAssistant, mock_pair_env: MagicMock, mock_identify: AsyncMock
) -> None:
    """Test the progress step while the spa has not answered yet."""
    event = asyncio.Event()

    async def _slow_pair(*args, **kwargs):
        await event.wait()
        return PairingResult(mac=MAC, ip=HOST)

    mock_pair_env.side_effect = _slow_pair
    result = await _start(hass, "pair")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], PAIR_INPUT
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    assert result["progress_action"] == "pairing"

    # Still waiting for the spa.
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.SHOW_PROGRESS

    event.set()
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    while result["type"] is FlowResultType.SHOW_PROGRESS_DONE:
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.CREATE_ENTRY
