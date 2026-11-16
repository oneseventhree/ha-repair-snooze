# Repair Snooze

**Home Assistant 2026.11+ custom integration · v1.0.0**

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

- Confirmed working in a Home Assistant installation by the repository owner and checked against **Home Assistant Core 2026.11.1** code and simulated lifecycle tests.
- Uses Home Assistant's internal repairs registry; future Home Assistant versions may change those APIs.
- It does not add a button to the built-in Repairs UI; snoozing is automatic.
- A forced stop or power loss can interrupt the delayed write of the latest snooze history.
- Uninstalling Repair Snooze un-ignores the repairs it recorded.

Please [report an issue](https://github.com/oneseventhree/ha-repair-snooze/issues) if the integration fails to load or does not identify a Marketplace repair.

## Source code

- `custom_components/repair_snooze/` — installable integration.
- `tests/test_lifecycle.py` — small self-contained unit tests using mock Home Assistant objects, not a full Home Assistant integration test environment.

**Safety:** Because this integration suppresses restart reminders, remember to restart Home Assistant after Marketplace updates when convenient.

## Versions and releases

Repair Snooze follows [Semantic Versioning](https://semver.org/):

- **Patch (1.0.1):** backwards-compatible bug fixes.
- **Minor (1.1.0):** backwards-compatible features or improvements.
- **Major (2.0.0):** breaking changes.

The installed integration's version is declared in `custom_components/repair_snooze/manifest.json`. Every stable version is published as a **GitHub Release** with a matching `vMAJOR.MINOR.PATCH` tag (for example, `v1.0.0`). Marketplace discovers release tags and shows the associated release notes.

For maintainers: update the manifest version and add a matching `## [MAJOR.MINOR.PATCH]` section to `CHANGELOG.md` in the same commit to `main`. The release workflow creates the tag and publishes the release automatically. Do not rewrite or reuse existing version tags.

See the [changelog](CHANGELOG.md) for release notes.
