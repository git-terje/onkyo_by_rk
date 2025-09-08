from __future__ import annotations

import logging
from typing import Optional
from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature
from homeassistant.components.media_player.const import MediaPlayerState
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import PlatformNotReady
from .const import DEFAULT_ZONE, DEFAULT_RESOLUTION
from .helpers import get_entry_data

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    try:
        _ = get_entry_data(hass, entry.entry_id)
    except Exception as exc:
        raise PlatformNotReady("Receiver not ready") from exc
    ent = OnkyoByRKMediaPlayer(entry.entry_id)
    async_add_entities([ent], update_before_add=False)

class OnkyoByRKMediaPlayer(MediaPlayerEntity):
    _attr_should_poll = False
    _attr_supported_features = (MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF | MediaPlayerEntityFeature.VOLUME_STEP | MediaPlayerEntityFeature.VOLUME_SET)

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self._state = MediaPlayerState.ON
        self._volume_level: float = 0.0

    @property
    def unique_id(self) -> str:
        return f"{self._entry_id}_media_player_main"

    @property
    def name(self) -> str:
        return "Onkyo by RK"

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def volume_level(self) -> Optional[float]:
        return self._volume_level

    def _res(self) -> int:
        from .helpers import get_entry_data
        caps = get_entry_data(self.hass, self._entry_id).get("caps", {})
        return int(caps.get("volume_resolution") or DEFAULT_RESOLUTION)

    def _recv(self):
        from .helpers import get_entry_data
        return get_entry_data(self.hass, self._entry_id)["receiver"]

    async def async_turn_on(self) -> None:
        await self._recv().turn_on(DEFAULT_ZONE)
        self._state = MediaPlayerState.ON
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        await self._recv().turn_off(DEFAULT_ZONE)
        self._state = MediaPlayerState.OFF
        self.async_write_ha_state()

    async def async_volume_up(self) -> None:
        await self._recv().volume_up(DEFAULT_ZONE)

    async def async_volume_down(self) -> None:
        await self._recv().volume_down(DEFAULT_ZONE)

    async def async_set_volume_level(self, volume: float) -> None:
        res = self._res()
        step = max(0, min(res, int(round(volume * res))))
        await self._recv().set_volume_step(step, zone=DEFAULT_ZONE)
        self._volume_level = step / float(res)
        self.async_write_ha_state()
