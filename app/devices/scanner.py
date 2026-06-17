"""Scanner driver — Datalogic Matrix (TCP) + Mock. Frame: STX + data + ETX."""
import asyncio
import logging
import random

from app.devices.base import BaseScanner

log = logging.getLogger("satori.scanner")

STX, ETX = b"\x02", b"\x03"


# ── REAL: Datalogic Matrix qua TCP ──
class RealScanner(BaseScanner):
    """Lắng nghe 1 scanner TCP. Mỗi mã đọc được gọi on_scan(ma).

    Để hỗ trợ nhiều scanner, DeviceManager tạo nhiều RealScanner cùng on_scan.
    """

    def __init__(self, on_scan, host, port):
        super().__init__(on_scan)
        self.host, self.port = host, port
        self._server = None

    async def start(self):
        async def handle(reader, writer):
            peer = writer.get_extra_info("peername")
            log.info("Scanner kết nối: %s", peer)
            buf = b""
            try:
                while True:
                    chunk = await reader.read(512)
                    if not chunk:
                        break
                    buf += chunk
                    while ETX in buf:
                        s = buf.find(STX) + 1 if STX in buf else 0
                        e = buf.find(ETX)
                        ma = buf[s:e].decode(errors="ignore").strip()
                        buf = buf[e + 1:]
                        if ma:
                            await self.on_scan(ma)
            finally:
                writer.close()

        self._server = await asyncio.start_server(handle, self.host, self.port)
        log.info("RealScanner lắng nghe %s:%s", self.host, self.port)
        async with self._server:
            await self._server.serve_forever()

    async def stop(self):
        if self._server:
            self._server.close()

    async def is_connected(self) -> bool:
        # Scanner ở chế độ server: coi như sẵn sàng khi server đang chạy.
        return self._server is not None and self._server.is_serving()


# ── MOCK: chờ inject từ API / auto random ──
class MockScanner(BaseScanner):
    def __init__(self, on_scan, name="mock"):
        super().__init__(on_scan)
        self.name = name
        self._running = False

    async def start(self):
        self._running = True
        log.info("MockScanner '%s' sẵn sàng (chờ inject_scan).", self.name)
        while self._running:
            await asyncio.sleep(0.5)

    async def stop(self):
        self._running = False

    async def is_connected(self) -> bool:
        return self._running

    async def inject_scan(self, ma_chai: str):
        """Gọi từ API test để giả lập 1 lần quét."""
        await self.on_scan(ma_chai)

    async def auto_random(self, count=10, delay=1.0):
        """Tự sinh mã ngẫu nhiên để test nhanh."""
        import datetime
        today = datetime.date.today()
        for _ in range(count):
            roll = random.random()
            if roll < 0.1:
                ma = "NOREAD"
            else:
                ma = today.strftime("%y%m%d") + str(random.randint(1, 50)).zfill(5)
            await self.on_scan(ma)
            await asyncio.sleep(delay)
