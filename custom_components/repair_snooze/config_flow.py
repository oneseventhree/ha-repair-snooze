"""Configuration flow for Repair Snooze."""

from homeassistant import config_entries

from .const import DOMAIN


class RepairSnoozeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up Repair Snooze once from the Home Assistant UI."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Confirm setup with no external credentials needed."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Repair Snooze", data={})

        return self.async_show_form(step_id="user")
