"""Laser printer driver — TCP gửi lệnh in + Mock."""
import asyncio
import logging

from app.devices.base import BaseLaser

log = logging.getLogger("satori.laser")


# ── REAL: TCP gửi lệnh in ──
class RealLaser(BaseLaser):
    def __init__(self, host, port):
        from app.config import settings
        self.host, self.port = host, port
        self._connected = False
        self._cmd_template = settings.laser_cmd_template

    async def connect(self):
        # Thử kết nối thật để biết laser có online không (không còn "ảo OK").
        self._connected = await self._probe()
        log.info("RealLaser %s:%s connected=%s template=%r",
                 self.host, self.port, self._connected, self._cmd_template)

    async def _probe(self) -> bool:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=2)
            writer.close()
            return True
        except Exception:
            return False

    async def print_code(self, ma_chai: str):
        cmd = self._cmd_template.format(code=ma_chai).encode()
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)
            writer.write(cmd)
            await writer.drain()
            writer.close()
            self._connected = True
            log.info("Laser print → %r", cmd)
        except Exception:
            # In thất bại → laser coi như mất kết nối (UI phản ánh ngay).
            self._connected = False
            raise

    async def is_connected(self) -> bool:
        return self._connected


# ── MOCK ──
class MockLaser(BaseLaser):
    def __init__(self):
        self._connected = True

    async def connect(self):
        log.info("[MOCK Laser] connected")

    async def print_code(self, ma_chai: str):
        log.info("[MOCK Laser] In mã: %s", ma_chai)

    async def is_connected(self) -> bool:
        return self._connected
