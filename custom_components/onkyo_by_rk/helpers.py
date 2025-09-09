from __future__ import annotations
from typing import Any, Dict
from homeassistant.core import HomeAssistant
from .const import DOMAIN

def get_entry_data(hass: HomeAssistant, entry_id: str) -> Dict[str, Any]:
    return hass.data[DOMAIN]["receivers"][entry_id]

def get_receiver(hass: HomeAssistant, entry_id: str):
    try:
        return hass.data[DOMAIN]["receivers"][entry_id]["receiver"]
    except Exception:
        pass
    try:
        return hass.data[DOMAIN][entry_id]["receiver"]
    except Exception as exc:
        raise KeyError(f"Receiver not found for entry_id={entry_id}") from exc
