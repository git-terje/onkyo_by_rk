from __future__ import annotations
from urllib.parse import urlparse
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback
from .const import DOMAIN, DEFAULT_PORT, DEFAULT_ZONE
from .eiscp import EiscpTransport, EiscpError

class OnkyoByRkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input.get("host", "").strip()
            port = int(user_input.get("port", DEFAULT_PORT))
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()
            t = EiscpTransport(host, port)
            try:
                await t.async_connect()
                if not await t.ping():
                    errors["base"] = "cannot_connect"
            except EiscpError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            finally:
                await t.async_close()
            if not errors:
                return self.async_create_entry(title=f"Onkyo @ {host}", data={"host": host, "port": port, "zone": DEFAULT_ZONE})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({vol.Required("host"): str, vol.Optional("port", default=DEFAULT_PORT): int}), errors=errors)

    async def async_step_ssdp(self, discovery_info) -> FlowResult:
        location = discovery_info.get("ssdp_location")
        host = None
        if location:
            try:
                host = urlparse(location).hostname
            except Exception:
                host = None
        if not host:
            for key in ("_host", "HOST", "host"):
                if key in discovery_info:
                    host = discovery_info.get(key)
                    break
        if not host:
            return self.async_abort(reason="cannot_connect")
        port = DEFAULT_PORT
        await self.async_set_unique_id(f"{host}:{port}")
        self._abort_if_unique_id_configured()
        self._discovered = {"host": host, "port": port}
        return await self.async_step_confirm()

    async def async_step_zeroconf(self, discovery_info) -> FlowResult:
        host = discovery_info.get("host") or (discovery_info.get("addresses", []) or [None])[0]
        if not host:
            return self.async_abort(reason="cannot_connect")
        port = DEFAULT_PORT
        await self.async_set_unique_id(f"{host}:{port}")
        self._abort_if_unique_id_configured()
        self._discovered = {"host": host, "port": port}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict | None = None) -> FlowResult:
        host = self._discovered["host"]
        port = self._discovered["port"]
        errors: dict[str, str] = {}
        if user_input is not None:
            t = EiscpTransport(host, port)
            try:
                await t.async_connect()
                if not await t.ping():
                    errors["base"] = "cannot_connect"
            except EiscpError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            finally:
                await t.async_close()
            if not errors:
                return self.async_create_entry(title=f"Onkyo @ {host}", data={"host": host, "port": port, "zone": DEFAULT_ZONE})
        return self.async_show_form(step_id="confirm", data_schema=vol.Schema({vol.Required("host", default=host): str, vol.Optional("port", default=port): int}), errors=errors)

    @callback
    def async_get_options_flow(self, config_entry):
        return OnkyoByRkOptionsFlow(config_entry)

class OnkyoByRkOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        return self.async_create_entry(title="Options", data={})
