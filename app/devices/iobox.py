"""IO-Box driver — ModBus TCP (điều khiển băng tải + đẩy loại) + Mock."""
import asyncio
import logging

from app.devices.base import BaseIOBox

log = logging.getLogger("satori.iobox")


# ── REAL: ModBus TCP ──
class RealIOBox(BaseIOBox):
    def __init__(self, host, port):
        from pymodbus.client import AsyncModbusTcpClient
        from app.config import settings
        self.host, self.port = host, port
        self.client = AsyncModbusTcpClient(host, port=port)
        self.coil_bang_tai = settings.iobox_coil_bang_tai
        self.coil_day_loai = settings.iobox_coil_day_loai
        self.pulse_width   = settings.iobox_pulse_width

    async def connect(self):
        await self.client.connect()
        log.info("RealIOBox connect %s:%s -> %s (coil_bang_tai=%s coil_day_loai=%s)",
                 self.host, self.port, self.client.connected,
                 self.coil_bang_tai, self.coil_day_loai)

    async def start_bang_tai(self):
        await self.client.write_coil(self.coil_bang_tai, True)

    async def stop_bang_tai(self):
        await self.client.write_coil(self.coil_bang_tai, False)

    async def day_loai_chai(self):
        await self.client.write_coil(self.coil_day_loai, True)
        await asyncio.sleep(self.pulse_width)
        await self.client.write_coil(self.coil_day_loai, False)

    async def is_connected(self) -> bool:
        return bool(self.client.connected)


# ── MOCK: chỉ in log ──
class MockIOBox(BaseIOBox):
    def __init__(self):
        self._connected = True

    async def connect(self):
        log.info("[MOCK IO-Box] connected")

    async def start_bang_tai(self):
        log.info("[MOCK IO-Box] Băng tải START")

    async def stop_bang_tai(self):
        log.info("[MOCK IO-Box] Băng tải STOP")

    async def day_loai_chai(self):
        log.info("[MOCK IO-Box] ►►► ĐẨY LOẠI CHAI ◄◄◄")

    async def is_connected(self) -> bool:
        return self._connected
