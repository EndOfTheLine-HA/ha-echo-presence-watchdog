# Echo presence watchdog

A Home Assistant package that tells you when your Echo presence switches stop updating.

It is for the setup where an Alexa routine turns a Home Assistant switch on when an Echo detects people, and a second routine turns it off. The method comes from NickC's 2022 community guide, [Simple way to get Amazon Echo 4th generation ultrasound motion/presence sensors into Home Assistant](https://community.home-assistant.io/t/394058). If Alexa loses the link between a routine and its switch, the routine keeps running but changes nothing, and the switch keeps its last state with no error anywhere. This package catches that.

Write-up: [Alexa Routines as Presence Sensors: How to Build Them and How They Quietly Break](https://homeautomated.net/investigations/alexa-routines-presence-sensors) on homeautomated.net.

## The setup it watches

- One switch per Echo that does nothing on its own. A template switch with no actions works (**Settings > Devices & services > Helpers > Create helper > Template > Switch**), and so does a Toggle helper.
- The switches exposed to Alexa through Home Assistant Cloud (**Settings > Voice assistants > Expose**).
- Two Alexa routines per Echo. In the Alexa app, open **Routines**, tap **+**, choose **Presence Detection** (under Events with People Recognition) and pick the Echo. **When** that Echo, **People are detected**, then **Alexa will** set the switch to **Power: On**. A second routine with **People aren't detected** and **Power: Off**.
- Only Echos the Alexa app offers for Presence Detection can do this. If the app shows **Set up now** next to an Echo, follow that prompt first.

## What it does

- Keeps one date and time helper per switch with the last time **Alexa** changed it. Only changes made by the Home Assistant Cloud user count, so a restart rewriting the state, or you toggling the switch in Home Assistant, cannot make a dead routine look alive.
- Every day at 9:00, sends a push for any switch Alexa has not changed in 24 hours, naming it and saying how to fix it.
- Skips the check while your alarm is armed away.
- Run "Echo presence - daily Alexa check" by hand and it sends an "all OK" push with every switch's age.

It ships as a package, not a blueprint, because it creates its own helpers and blueprints cannot.

## Requirements

- Home Assistant exposed to Alexa through Home Assistant Cloud.
- One presence switch (or Toggle helper) per Echo, changed by Alexa routines.
- A notify action that reaches your phone, for example from the Home Assistant Companion app.

## Install

1. If you don't use packages yet, add this to `configuration.yaml` and create a `packages` folder next to it:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

2. Copy [`packages/echo_presence_watchdog.yaml`](packages/echo_presence_watchdog.yaml) into your `packages` folder.
3. Open it and change everything marked `CHANGE ME`:
   1. your switch entity ids,
   2. your Home Assistant Cloud user id (next section),
   3. your notify action (it appears twice),
   4. your alarm entity, or delete that condition.

   The file comes with four sample rooms. Each room appears in four places: its helper, the trigger list, the switch-to-helper map, and the daily check's list. Keep those in step, and delete sample rooms you don't use from all four.
4. Check the configuration (**Developer tools > YAML > Check configuration**), then restart, or reload **Automations** and **Input datetimes**.
5. In each room, let Alexa turn the switch on and then off (walk in, then leave, or run each routine from the Alexa app). That room's "last Alexa update" helper should jump to the current time after each change. If the switch changes but the helper doesn't, check the user id and the switch-to-helper map. If the switch doesn't change, check the routine.

## Find your Home Assistant Cloud user id

1. Let Alexa change one of your presence switches from off to on or on to off: walk into the room, or run the routine from the Alexa app.
2. Straight away, in **Developer tools > Template**, enter (with your own switch):

   ```
   {{ states.switch.kitchen_presence.context.user_id }}
   ```

3. Copy the 32-character string it shows into the package in place of `YOUR_HA_CLOUD_USER_ID`.

If it shows `None`, or the id of your own user, the last change didn't come from Alexa. Trigger it from Alexa again and re-check straight away.

Use this method rather than the Users page. With advanced mode on, **Settings > People > Users** lists "Home Assistant Cloud" and shows its id when you open it, but an instance can have more than one such user, and only one of them is the user Alexa's changes come from. With the wrong id, every switch alerts every morning.

## Limits

- A room nobody enters for a whole day alerts even though nothing is broken. So does a room someone never leaves, because its switch stays on. Raise `max_age_hours` or leave that room out.
- A new date and time helper may start at midnight today rather than "never", so on install day a broken routine is not flagged until the next morning. Step 5 of the install covers that.
- If you relink Home Assistant Cloud and its user id changes, the helpers stop updating and you get an alert. Update the id.
- Using the manual Alexa skill instead of Home Assistant Cloud? Alexa's changes should carry the user that owns the skill's access token. Untested.

## Remove

Delete the file, then reload **Automations** and **Input datetimes** (or restart).

## Tests

`pytest` loads the package into a real Home Assistant (no network, no devices) and checks that Alexa's changes are recorded, that restarts and your own changes are not, that stale switches alert, and that the alarm and manual-run paths behave. See [`.github/workflows/validate.yml`](.github/workflows/validate.yml) for the pinned versions.

## Credit

The presence-switch method is NickC's, from the Home Assistant community (2022). This package only watches it.

## License

MIT. See [LICENSE](LICENSE).
