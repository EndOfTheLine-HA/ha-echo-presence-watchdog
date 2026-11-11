"""Behavior of the Echo presence watchdog package in a real Home Assistant."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.automation import DATA_COMPONENT
from homeassistant.core import Context, HomeAssistant
from homeassistant.util import dt as dt_util

from .conftest import ALARM, CLOUD_USER

KITCHEN = "switch.kitchen_presence"
KITCHEN_HELPER = "input_datetime.echo_presence_kitchen_last_alexa"
HELPERS = {
    "Kitchen": KITCHEN_HELPER,
    "Desk": "input_datetime.echo_presence_desk_last_alexa",
    "Dashboard": "input_datetime.echo_presence_dashboard_last_alexa",
    "Bedroom": "input_datetime.echo_presence_bedroom_last_alexa",
}
CHECK = "automation.echo_presence_daily_alexa_check"


def stamp(hass: HomeAssistant, helper: str) -> float | None:
    return hass.states.get(helper).attributes.get("timestamp")


async def set_ages(hass: HomeAssistant, **hours_ago: float) -> None:
    """Set each room's last Alexa update to that many hours ago."""
    for room, hours in hours_ago.items():
        when = dt_util.now() - timedelta(hours=hours)
        await hass.services.async_call(
            "input_datetime",
            "set_datetime",
            {"entity_id": HELPERS[room], "timestamp": when.timestamp()},
            blocking=True,
        )


async def run_check(hass: HomeAssistant, *, daily: bool) -> None:
    """Run the daily check as the 9:00 trigger would, or as a manual Run from the UI."""
    automation = hass.data[DATA_COMPONENT].get_entity(CHECK)
    run_variables = {"trigger": {"platform": "time", "id": "daily"}} if daily else {"trigger": {"platform": None}}
    await automation.async_trigger(run_variables, skip_condition=False)
    await hass.async_block_till_done()


async def test_alexa_change_is_recorded(hass, watchdog):
    await set_ages(hass, Kitchen=48)
    before = stamp(hass, KITCHEN_HELPER)
    hass.states.async_set(KITCHEN, "on", context=Context(user_id=CLOUD_USER))
    await hass.async_block_till_done()
    after = stamp(hass, KITCHEN_HELPER)
    assert after > before
    assert abs(after - dt_util.now().timestamp()) < 5


async def test_restarts_and_other_users_are_ignored(hass, watchdog):
    await set_ages(hass, Kitchen=48)
    before = stamp(hass, KITCHEN_HELPER)
    # A restart restoring the state has no user; a change from the app has the person's user.
    hass.states.async_set(KITCHEN, "on", context=Context())
    hass.states.async_set(KITCHEN, "off", context=Context(user_id="fedcba9876543210fedcba9876543210"))
    await hass.async_block_till_done()
    assert stamp(hass, KITCHEN_HELPER) == before


async def test_stale_switch_alerts_at_nine(hass, watchdog):
    await set_ages(hass, Kitchen=1, Desk=2, Dashboard=3, Bedroom=30)
    await run_check(hass, daily=True)
    assert len(watchdog) == 1
    push = watchdog[0].data
    assert push["title"] == "Echo presence: Alexa stopped updating"
    assert "for Bedroom" in push["message"]
    assert "Kitchen 1.0 h ago" in push["message"]


async def test_nothing_is_sent_at_nine_when_all_is_well(hass, watchdog):
    await set_ages(hass, Kitchen=1, Desk=2, Dashboard=3, Bedroom=4)
    await run_check(hass, daily=True)
    assert watchdog == []


async def test_manual_run_sends_a_status_push(hass, watchdog):
    await set_ages(hass, Kitchen=1, Desk=2, Dashboard=3, Bedroom=4)
    await run_check(hass, daily=False)
    assert len(watchdog) == 1
    assert watchdog[0].data["title"] == "Echo presence check: all OK"
    assert "Bedroom 4.0 h ago" in watchdog[0].data["message"]


async def test_check_is_skipped_while_armed_away(hass, watchdog):
    await set_ages(hass, Kitchen=30, Desk=30, Dashboard=30, Bedroom=30)
    hass.states.async_set(ALARM, "armed_away")
    await run_check(hass, daily=True)
    assert watchdog == []
