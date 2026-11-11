"""A real Home Assistant instance that loads the package from this repository.

Nothing here touches a real house: the presence switches, the alarm and the phone are plain
states and a stand-in notify action set up by the tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant import config as config_util
from homeassistant import loader
from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import (
    area_registry,
    category_registry,
    condition,
    device_registry,
    entity,
    entity_registry,
    floor_registry,
    frame,
    issue_registry,
    label_registry,
    restore_state,
    template,
    translation,
    trigger,
)
from homeassistant.setup import async_setup_component
from homeassistant.util.yaml import parse_yaml

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "packages" / "echo_presence_watchdog.yaml"
CLOUD_USER = "0123456789abcdef0123456789abcdef"
SWITCHES = ["switch.kitchen_presence", "switch.desk_presence", "switch.dashboard_presence", "switch.bedroom_presence"]
ALARM = "alarm_control_panel.your_alarm"


def package_config() -> dict:
    """The package as a user would install it, with a made-up Home Assistant Cloud user id."""
    text = PACKAGE.read_text(encoding="utf-8")
    assert text.count("YOUR_HA_CLOUD_USER_ID") == 1
    return parse_yaml(text.replace("YOUR_HA_CLOUD_USER_ID", CLOUD_USER))


@pytest.fixture
async def hass(tmp_path):
    instance = HomeAssistant(str(tmp_path))
    instance.config_entries = ConfigEntries(instance, {})
    # The same core helpers Home Assistant's bootstrap sets up before integrations load.
    loader.async_setup(instance)
    entity.async_setup(instance)
    frame.async_setup(instance)
    template.async_setup(instance)
    translation.async_setup(instance)
    device_registry.async_setup(instance)
    for registry in (
        area_registry,
        category_registry,
        device_registry,
        entity_registry,
        floor_registry,
        issue_registry,
        label_registry,
        restore_state,
    ):
        await registry.async_load(instance, load_empty=True)
    await condition.async_setup(instance)
    await trigger.async_setup(instance)
    # No web server or frontend in these tests.
    instance.config.skip_pip = True
    instance.config.components.update({"http", "websocket_api", "frontend"})
    await instance.async_start()
    yield instance
    await instance.async_stop(force=True)


@pytest.fixture
async def watchdog(hass: HomeAssistant) -> list[ServiceCall]:
    """Install the package the way Home Assistant merges packages, and capture its pushes."""
    pushes: list[ServiceCall] = []

    async def capture(call: ServiceCall) -> None:
        pushes.append(call)

    hass.services.async_register("notify", "mobile_app_your_phone", capture)
    for switch in SWITCHES:
        hass.states.async_set(switch, "off")
    hass.states.async_set(ALARM, "disarmed")

    merged = await config_util.merge_packages_config(
        hass, {"homeassistant": {}}, {"echo_presence_watchdog": package_config()}
    )
    assert await async_setup_component(hass, "input_datetime", {"input_datetime": merged["input_datetime"]})
    assert await async_setup_component(hass, "automation", {"automation": merged["automation"]})
    await hass.async_block_till_done()
    for automation_id in ("echo_presence_record_alexa_update", "echo_presence_daily_alexa_check"):
        assert hass.states.get(f"automation.{automation_id}").state == "on"
    return pushes
