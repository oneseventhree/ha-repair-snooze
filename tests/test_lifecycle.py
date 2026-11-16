"""Dependency-free lifecycle tests; use Python 3.13+ (Home Assistant 2026.11)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Minimal subset of the HA API. The implementation is tested with fakes here,
# *not* claimed to have been run inside a full Home Assistant deployment.
ha = ModuleType('homeassistant')
ha.__path__ = []
config_entries = ModuleType('homeassistant.config_entries')
core = ModuleType('homeassistant.core')
helpers = ModuleType('homeassistant.helpers')
helpers.__path__ = []
ir = ModuleType('homeassistant.helpers.issue_registry')
storage = ModuleType('homeassistant.helpers.storage')

class ConfigEntry:
    def __init__(self): self.unsubs = []
    def async_on_unload(self, func): self.unsubs.append(func)
    def async_unload_callbacks(self):
        for un in self.unsubs: un()
        self.unsubs.clear()

@dataclass
class Issue:
    domain: str
    issue_id: str
    translation_key: str
    active: bool = True
    dismissed_version: str | None = None

class Registry:
    def __init__(self, bus, issues):
        self.issues = {(v.domain,v.issue_id): v for v in issues}
        self.bus = bus
    def async_get_issue(self, domain, issue_id):
        return self.issues.get((domain, issue_id))
    def async_ignore(self, domain, issue_id, ignore):
        issue = self.issues[(domain,issue_id)]
        issue.dismissed_version = '2026.11' if ignore else None
        self.bus.fire('repairs_issue_registry_updated', {'action':'update','domain':domain,'issue_id':issue_id})

class Bus:
    def __init__(self): self.subs={}
    def async_listen(self, typ, cb):
        self.subs.setdefault(typ, []).append(cb)
        def un(): self.subs[typ].remove(cb)
        return un
    def fire(self,typ,data):
        for cb in list(self.subs.get(typ, [])): cb(SimpleNamespace(data=data))

class HA:
    def __init__(self, disk, issues):
        self.data = {}
        self.disk = disk
        self.bus = Bus()
        self.registry = Registry(self.bus, issues)

class Store:
    def __init__(self,hass,version,key,**kwargs):
        self.hass, self.key = hass,key
    async def async_load(self): return self.hass.disk.get(self.key)
    async def async_save(self, value): self.hass.disk[self.key] = value
    def async_delay_save(self, func, delay): self.hass.disk[self.key]=func()
    async def async_remove(self): self.hass.disk.pop(self.key,None)

class ConfigFlow:
    def __init_subclass__(cls, **kwargs): pass

ha.config_entries = config_entries
ha.core = core
ha.helpers = helpers
config_entries.ConfigEntry = ConfigEntry
config_entries.ConfigFlow = ConfigFlow
core.Event = object
core.HomeAssistant = HA
core.callback = lambda f: f
ir.IssueEntry = Issue
ir.EVENT_REPAIRS_ISSUE_REGISTRY_UPDATED = 'repairs_issue_registry_updated'
ir.async_get = lambda hass: hass.registry
storage.Store = Store
for name,obj in {
    'homeassistant':ha,
    'homeassistant.config_entries':config_entries,
    'homeassistant.core':core,
    'homeassistant.helpers':helpers,
    'homeassistant.helpers.issue_registry':ir,
    'homeassistant.helpers.storage':storage,
}.items(): sys.modules[name]=obj

component = importlib.import_module('custom_components.repair_snooze')

class RepairSnoozeTests(unittest.IsolatedAsyncioTestCase):
    async def test_initial_hide_is_strict_and_restores_on_new_process(self):
        disk = {}
        issues=[
            Issue('marketplace','restart_required_1_v1','restart_required'),
            Issue('marketplace','restart_required_2_v2','restart_required',dismissed_version='manually'),
            Issue('marketplace','critical_3','critical'),
            Issue('marketplace','restart_required_4_v4','other'),
            Issue('other','restart_required_5_v5','restart_required'),
        ]
        hass=HA(disk,issues)
        entry=ConfigEntry()
        await component.async_setup_entry(hass,entry)
        self.assertEqual(issues[0].dismissed_version,'2026.11')
        self.assertEqual(issues[1].dismissed_version,'manually')
        self.assertIsNone(issues[2].dismissed_version)
        self.assertIsNone(issues[3].dismissed_version)
        self.assertIsNone(issues[4].dismissed_version)
        self.assertEqual(disk['repair_snooze.ignored_issues']['ignored_ids'],['restart_required_1_v1'])
        # New Marketplace issue after update -> auto-hide.
        fresh=Issue('marketplace','restart_required_6_v6','restart_required')
        hass.registry.issues[(fresh.domain,fresh.issue_id)]=fresh
        hass.bus.fire('repairs_issue_registry_updated',{'action':'create','domain':'marketplace','issue_id':fresh.issue_id})
        self.assertEqual(fresh.dismissed_version,'2026.11')
        # A config-entry reload is not a restart; snoozes are retained.
        self.assertTrue(await component.async_unload_entry(hass,entry))
        entry=ConfigEntry()
        await component.async_setup_entry(hass,entry)
        self.assertEqual(fresh.dismissed_version,'2026.11')
        self.assertEqual(issues[0].dismissed_version,'2026.11')
        self.assertEqual(len(hass.bus.subs['repairs_issue_registry_updated']),1)
        # Actual new HA process: registry remembers ignored state, but inactive.
        await component.async_unload_entry(hass,entry)
        for issue in issues+[fresh]: issue.active=False
        restarted=HA(disk,issues+[fresh])
        entry2=ConfigEntry()
        await component.async_setup_entry(restarted,entry2)
        self.assertIsNone(issues[0].dismissed_version)
        self.assertIsNone(fresh.dismissed_version)
        self.assertEqual(issues[1].dismissed_version,'manually')
        self.assertEqual(disk['repair_snooze.ignored_issues']['ignored_ids'],[])
        # Same repository/version can be snoozed after a future update.
        fresh.active=True
        restarted.bus.fire('repairs_issue_registry_updated',{'action':'update','domain':'marketplace','issue_id':fresh.issue_id})
        self.assertEqual(fresh.dismissed_version,'2026.11')
        # Uninstall restores only tracked ignores.
        await component.async_unload_entry(restarted,entry2)
        await component.async_remove_entry(restarted,entry2)
        self.assertIsNone(fresh.dismissed_version)
        self.assertEqual(issues[1].dismissed_version,'manually')
        self.assertNotIn('repair_snooze.ignored_issues', disk)

    async def test_only_marketplace_restart_uninstall_is_allowed(self):
        issue=Issue('marketplace','restart_required_99_uninstall','restart_required_uninstall')
        hass=HA({},[issue])
        await component.async_setup_entry(hass,ConfigEntry())
        self.assertEqual(issue.dismissed_version, '2026.11')

if __name__=='__main__': unittest.main()
