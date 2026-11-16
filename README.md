# Repair Snooze

**Experimental custom integration for Home Assistant 2026.11 and newer.**

Automatically hides **Marketplace "Restart required" repairs** after you update or install a custom integration, until the next Home Assistant restart. It never performs or prevents a restart.

## Features

- Automatically snoozes Marketplace restart reminders, including those for HyperHDR, Alexa Media Player, DeLonghi BLE, and other Marketplace integrations.
- Hides existing Marketplace restart repairs when you first configure it.
- Does not hide unrelated repairs, errors, or deprecation warnings.
- Restores only its own ignored repairs on the next **real Home Assistant restart** (the old restart reminders normally become inactive at that point).
- Does not overwrite repairs you ignored manually.
- A config-entry reload does not count as a Home Assistant restart.

## Install through Home Assistant Marketplace

1. Open **Settings → Marketplace** (Home Assistant 2026.11+).
2. Select **Add from link**.
3. Enter `https://github.com/oneseventhree/ha-repair-snooze` and select **Add**. If asked, choose **Integration**.
4. Open **Repair Snooze** and select **Install**.
5. If Home Assistant requests it, restart to load the integration.
6. Open **Settings → Devices & services → Add integration**, find **Repair Snooze**, and finish its one-step setup.

<!-- ha-marketplace:exclude-start -->
### Manual installation

Copy `custom_components/repair_snooze` to `/config/custom_components/repair_snooze`, restart Home Assistant, then add **Repair Snooze** under **Settings → Devices & services**.

<!-- ha-marketplace:exclude-end -->

## How it works

The integration listens to Home Assistant's repair issue registry and targets only active `marketplace` issues whose ID starts with `restart_required_` and whose translation key is `restart_required` or `restart_required_uninstall`. It uses the registry's ignore mechanism and records which IDs it ignored. On the next Home Assistant process start, it un-ignores those tracked issues only.

Marketplace integration updates **still require a restart to activate the new code**. Hiding a reminder does not apply the update, and may hide the fact that new code is waiting.

## Compatibility and limitations

- Tested against **Home Assistant Core 2026.11.1 source** and local simulated lifecycle tests; **not tested yet on a live Home Assistant installation**.
- This is an **experimental** integration using internal registry details that may change in later releases.
- It does not add a button to the built-in Repairs UI; snoozing is automatic.
- A forced stop or power loss can interrupt the delayed write of the latest snooze history.
- Uninstalling Repair Snooze un-ignores the repairs it recorded.

Please [report an issue](https://github.com/oneseventhree/ha-repair-snooze/issues) if the integration fails to load or does not identify a Marketplace repair.

## Source code

- `custom_components/repair_snooze/` — installable integration.
- `tests/test_lifecycle.py` — small self-contained unit tests using mock Home Assistant objects, not a full Home Assistant integration test environment.

**Safety:** Because this integration suppresses restart reminders, remember to restart Home Assistant after Marketplace updates when convenient.
