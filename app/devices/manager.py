"""Quản lý tất cả thiết bị. Khởi tạo đúng mock/real theo config.

Hỗ trợ NHIỀU scanner (yêu cầu: tủ PLC nối 3 máy scan). Tất cả scanner
dùng chung 1 callback on_scan → backend xử lý đồng nhất.
"""
import asyncio
import logging

from app.config import settings
from app.devices import iobox, laser, scanner

log = logging.getLogger("satori.devices")


class DeviceManager:
    def __init__(self):
        self.scanners: list = []   # danh sách scanner (1 hoặc nhiều)
        self.iobox = None
        self.laser = None
        self._scanner_tasks: list[asyncio.Task] = []

    def setup(self, on_scan):
        if settings.use_mock_devices:
            # 1 mock scanner là đủ cho dev; vẫn để dạng list cho đồng nhất.
            self.scanners = [scanner.MockScanner(on_scan, name="mock-1")]
            self.iobox = iobox.MockIOBox()
            self.laser = laser.MockLaser()
            log.info("DeviceManager: chế độ MOCK")
        else:
            self.scanners = [
                scanner.RealScanner(on_scan, host, port)
                for host, port in settings.scanner_list
            ]
            self.iobox = iobox.RealIOBox(settings.iobox_host, settings.iobox_port)
            self.laser = laser.RealLaser(settings.laser_host, settings.laser_port)
            log.info("DeviceManager: chế độ REAL, %d scanner(s)",
                     len(self.scanners))

    @property
    def scanner(self):
        """Tiện truy cập scanner đầu tiên (vd để inject_scan khi test mock)."""
        return self.scanners[0] if self.scanners else None

    async def connect_all(self):
        if self.iobox:
            await self.iobox.connect()
        if self.laser:
            await self.laser.connect()

    async def start_scanners(self):
        for sc in self.scanners:
            self._scanner_tasks.append(asyncio.create_task(sc.start()))

    async def stop_scanners(self):
        for sc in self.scanners:
            await sc.stop()
        for t in self._scanner_tasks:
            t.cancel()
        self._scanner_tasks.clear()

    async def status(self) -> dict:
        scanner_ok = False
        if self.scanners:
            results = [await sc.is_connected() for sc in self.scanners]
            scanner_ok = all(results) and len(results) > 0
        return {
            "scanner": "OK" if scanner_ok else "OFFLINE",
            "scanner_count": len(self.scanners),
            "iobox": "OK" if (self.iobox and await self.iobox.is_connected())
                     else "OFFLINE",
            "laser": "OK" if (self.laser and await self.laser.is_connected())
                     else "OFFLINE",
        }


# Singleton dùng toàn app
device_manager = DeviceManager()
