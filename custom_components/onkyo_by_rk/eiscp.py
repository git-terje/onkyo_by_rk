from __future__ import annotations
import asyncio, logging
from dataclasses import dataclass
from typing import Optional

_LOGGER = logging.getLogger(__name__)
ISCP_MAGIC = b"ISCP"
ISCP_VERSION = 0x01

@dataclass
class EiscpFrame:
    data: bytes

class EiscpError(Exception): pass

class EiscpTransport:
    """Minimal eISCP transport for Onkyo/Pioneer network receivers."""

    def __init__(self, host: str, port: int, *, logger: Optional[logging.Logger] = None) -> None:
        self._host, self._port = host, int(port)
        self._logger = logger or _LOGGER
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def async_connect(self, timeout: float = 5.0) -> None:
        if self.connected:
            return
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port), timeout=timeout
            )
        except Exception as exc:
            raise EiscpError(f"Failed to connect to {self._host}:{self._port}") from exc

    async def async_close(self) -> None:
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            finally:
                self._reader = None
                self._writer = None

    @staticmethod
    def _build_payload(command: str, argument: Optional[str], zone: str) -> bytes:
        # eISCP payload like: !1PWRQSTN  or !1MVLUP
        cmd = f"!{zone}{command}{'' if argument is None else argument}\r"
        return cmd.encode("ascii")

    @staticmethod
    def _build_frame(payload: bytes) -> bytes:
        # ISCP header (16 bytes) + payload
        return b"ISCP" + (16).to_bytes(4,"big") + len(payload).to_bytes(4,"big") + bytes([0x01,0,0,0]) + payload

    async def _read_frame(self, timeout: float = 3.0) -> EiscpFrame:
        assert self._reader is not None
        r = self._reader
        magic = await asyncio.wait_for(r.readexactly(4), timeout=timeout)
        if magic != b"ISCP":
            raise EiscpError(f"Bad magic: {magic!r}")
        header_size = int.from_bytes(await r.readexactly(4), "big")
        data_size = int.from_bytes(await r.readexactly(4), "big")
        version = (await r.readexactly(1))[0]
        _ = await r.readexactly(3)  # reserved
        if header_size != 16 or version != 0x01:
            raise EiscpError("Unexpected header/version")
        payload = await asyncio.wait_for(r.readexactly(data_size), timeout=timeout)
        return EiscpFrame(data=payload)

    async def async_command(self, command: str, argument: Optional[str] = None, *, zone: str = "1", read_response: bool = True, timeout: float = 3.0) -> Optional[str]:
        async with self._lock:
            if not self.connected:
                await self.async_connect()
            frame = self._build_frame(self._build_payload(command, argument, zone))
            assert self._writer is not None
            self._writer.write(frame)
            await self._writer.drain()
            if not read_response:
                return None
            try:
                resp = await self._read_frame(timeout=timeout)
            except asyncio.TimeoutError:
                return None
            raw = resp.data.decode("ascii", errors="ignore")
            _LOGGER.debug("RAW-RESP: %r", raw)
            return raw

    async def async_query(self, command: str, *, zone: str = "1", timeout: float = 3.0) -> Optional[str]:
        return await self.async_command(command, "QSTN", zone=zone, read_response=True, timeout=timeout)

    async def ping(self) -> bool:
        try:
            raw = await self.async_query("PWR")
            return raw is not None and "PWR" in raw
        except Exception:
            return False

    # Convenience commands
    async def turn_on(self, zone: str = "1") -> None:
        await self.async_command("PWR", "01", zone=zone, read_response=False)
    async def turn_off(self, zone: str = "1") -> None:
        await self.async_command("PWR", "00", zone=zone, read_response=False)
    async def volume_up(self, zone: str = "1") -> None:
        await self.async_command("MVL", "UP", zone=zone, read_response=False)
    async def volume_down(self, zone: str = "1") -> None:
        await self.async_command("MVL", "DOWN", zone=zone, read_response=False)
    async def set_volume_step(self, step: int, zone: str = "1") -> None:
        step = max(0, min(255, int(step)))
        arg = f"{step:02X}"
        await self.async_command("MVL", arg, zone=zone, read_response=False)
