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
        self._connected = True
        log.info("RealLaser ready %s:%s  template=%r", self.host, self.port, self._cmd_template)

    async def print_code(self, ma_chai: str):
        cmd = self._cmd_template.format(code=ma_chai).encode()
        reader, writer = await asyncio.open_connection(self.host, self.port)
        writer.write(cmd)
        await writer.drain()
        writer.close()
        log.info("Laser print → %r", cmd)

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
