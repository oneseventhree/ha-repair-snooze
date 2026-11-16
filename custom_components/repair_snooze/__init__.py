"""Automatically snooze Marketplace restart repairs until the next HA restart.

Only issues created by Home Assistant's Marketplace and explicitly labeled as
restart-required are targeted. We keep a list of issues *we* ignored, so we can
undo those ignores on the next HA process start without touching user ignores.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    MARKETPLACE_DOMAIN,
    RESTART_ISSUE_PREFIX,
    RESTART_TRANSLATION_KEYS,
    STORE_KEY,
)

_LOGGER = logging.getLogger(__name__)


def _is_target(issue: ir.IssueEntry | None) -> bool:
    """Identify ONLY active Marketplace restart repairs, not other repairs."""
    return bool(
        issue is not None
        and issue.active
        and issue.domain == MARKETPLACE_DOMAIN
        and issue.issue_id.startswith(RESTART_ISSUE_PREFIX)
        and issue.translation_key in RESTART_TRANSLATION_KEYS
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Start hiding Marketplace restart repairs generated in this HA run."""
    # hass.data survives config-entry reloads but not a Home Assistant restart.
    # This lets us distinguish an actual restart from a harmless reload.
    runtime = hass.data.setdefault(DOMAIN, {"boot_id": uuid4().hex})
    boot_id: str = runtime["boot_id"]
    store: Store[dict] = Store(hass, 1, STORE_KEY, atomic_writes=True)
    saved = await store.async_load() or {}
    registry = ir.async_get(hass)
    previous_boot = saved.get("boot_id")
    ignored_ids: set[str] = set(saved.get("ignored_ids", []))
    first_install = previous_boot is None

    if previous_boot != boot_id:
        # A new HA process started: undo *only* our temporary ignores. Older
        # non-persistent repairs will usually be inactive by now, as intended.
        for issue_id in ignored_ids:
            issue = registry.async_get_issue(MARKETPLACE_DOMAIN, issue_id)
            if issue is not None and issue.dismissed_version is not None:
                registry.async_ignore(MARKETPLACE_DOMAIN, issue_id, False)
        ignored_ids.clear()
        await store.async_save({"boot_id": boot_id, "ignored_ids": []})

    def schedule_save() -> None:
        """Coalesce writes; HA flushes these on graceful shutdown."""
        payload = {"boot_id": boot_id, "ignored_ids": sorted(ignored_ids)}
        store.async_delay_save(lambda: payload, delay=1)

    @callback
    def snooze(issue_id: str) -> None:
        """Ignore a valid repair unless it has already been ignored by someone."""
        issue = registry.async_get_issue(MARKETPLACE_DOMAIN, issue_id)
        if not _is_target(issue) or issue.dismissed_version is not None:
            return
        ignored_ids.add(issue_id)
        schedule_save()
        registry.async_ignore(MARKETPLACE_DOMAIN, issue_id, True)
        _LOGGER.info("Snoozed Marketplace restart repair: %s", issue_id)

    @callback
    def issue_changed(event: Event) -> None:
        """React to new/re-raised repairs, not to other registries or removals."""
        data = event.data
        if (
            data.get("domain") == MARKETPLACE_DOMAIN
            and data.get("action") in ("create", "update")
            and isinstance(data.get("issue_id"), str)
        ):
            snooze(data["issue_id"])

    # Register first so future Marketplace installs are caught immediately.
    entry.async_on_unload(
        hass.bus.async_listen(ir.EVENT_REPAIRS_ISSUE_REGISTRY_UPDATED, issue_changed)
    )

    # First installation hides the four existing repairs from the screenshot.
    # On subsequent full restarts don't re-hide stale start-up issues: the
    # existing snoozes expire, and newly updated integrations get new snoozes.
    # Reloads within the same HA process may catch issues created while off.
    if first_install or previous_boot == boot_id:
        for issue in list(registry.issues.values()):
            if _is_target(issue):
                snooze(issue.issue_id)

    # Keep a reference for uninstall cleanup. It is not removed on reload.
    runtime["ignored_ids"] = ignored_ids
    runtime["store"] = store
    _LOGGER.debug("Repair Snooze ready; %d repairs hidden", len(ignored_ids))


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Stop listening. A reload is not a HA restart and keeps snoozes."""
    entry.async_unload_callbacks()
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Restore our snoozed issues if the user removes the integration."""
    registry = ir.async_get(hass)
    runtime = hass.data.get(DOMAIN, {})
    store: Store[dict] = runtime.get("store") or Store(
        hass, 1, STORE_KEY, atomic_writes=True
    )
    saved = await store.async_load() or {}
    issue_ids = set(saved.get("ignored_ids", []))
    issue_ids.update(runtime.get("ignored_ids", set()))
    for issue_id in issue_ids:
        issue = registry.async_get_issue(MARKETPLACE_DOMAIN, issue_id)
        if issue is not None and issue.dismissed_version is not None:
            registry.async_ignore(MARKETPLACE_DOMAIN, issue_id, False)
    await store.async_remove()
    hass.data.pop(DOMAIN, None)
