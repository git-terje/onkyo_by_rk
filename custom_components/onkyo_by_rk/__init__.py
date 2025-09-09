from __future__ import annotations

import json, logging, os
from pathlib import Path
from typing import Any, Dict, List

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS, DEFAULT_PORT, DEFAULT_ZONE, DEFAULT_RESOLUTION
from .eiscp import EiscpTransport
from .helpers import get_receiver

_LOGGER = logging.getLogger(__name__)

PROBE_COMMANDS = [("PWR", None), ("MVL", None), ("AMT", None), ("SLI", None), ("LMD", None), ("ZPW", None), ("ZVL", None), ("ZMT", None)]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("receivers", {})

    async def handle_debug_files(call: ServiceCall):
        comp_dir = Path(hass.config.path("custom_components/onkyo_by_rk"))
        files: List[str] = []
        if comp_dir.exists():
            for root, _, filenames in os.walk(comp_dir):
                for fn in filenames:
                    rel = str(Path(root) / fn).replace(str(hass.config.path("")) + "/", "")
                    files.append(rel)
        files.sort()
        _LOGGER.warning("Onkyo by RK debug_files: %s", files)

    hass.services.async_register(DOMAIN, "debug_files", handle_debug_files)
    return True

async def _probe_caps(transport: EiscpTransport) -> Dict[str, Any]:
    return {"volume_resolution": DEFAULT_RESOLUTION, "inputs": {}, "zones": ["1"]}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data.get("host")
    port = entry.data.get("port", DEFAULT_PORT)
    transport = EiscpTransport(host, port, logger=_LOGGER)

    try:
        await transport.async_connect()
        if not await transport.ping():
            raise RuntimeError("Receiver did not respond to PWRQSTN")
    except Exception as exc:
        _LOGGER.exception("Failed to connect to Onkyo %s:%s", host, port)
        raise ConfigEntryNotReady from exc

    caps = await _probe_caps(transport)

    hass.data[DOMAIN]["receivers"][entry.entry_id] = {
        "receiver": transport, "host": host, "port": port, "caps": caps, "model": None
    }
    hass.data[DOMAIN][entry.entry_id] = {"receiver": transport, "caps": caps}

    async def _eid(call: ServiceCall) -> str:
        return str(call.data.get("entry_id") or entry.entry_id)

    async def handle_dump_capabilities(call: ServiceCall):
        eid = await _eid(call)
        recv = get_receiver(hass, eid)
        results: dict[str, Any] = {"host": host, "port": port, "zone": DEFAULT_ZONE, "raw": {}}
        for cmd, _ in PROBE_COMMANDS:
            results["raw"][cmd] = await recv.async_query(cmd, zone=DEFAULT_ZONE)
        out_dir = Path(hass.config.path("onkyo_by_rk"))
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{eid}_probe.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        _LOGGER.warning("Onkyo by RK probe written: %s", out_dir / f"{eid}_probe.json")

    hass.services.async_register(DOMAIN, "dump_capabilities", handle_dump_capabilities)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_update_listener))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from homeassistant.helpers.entity_component import async_unload_platforms
    unload_ok = await async_unload_platforms(hass, PLATFORMS)
    rec = hass.data.get(DOMAIN, {}).get("receivers", {}).pop(entry.entry_id, None)
    if rec and (receiver := rec.get("receiver")):
        await receiver.async_close()
    if entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    if not hass.data.get(DOMAIN, {}).get("receivers"):
        hass.services.async_remove(DOMAIN, "dump_capabilities")
        hass.services.async_remove(DOMAIN, "debug_files")
    return unload_ok

async def _update_listener(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)
