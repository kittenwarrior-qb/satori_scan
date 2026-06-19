"""Scanner driver — Datalogic Matrix (TCP) + Mock. Frame: STX + data + ETX."""
import asyncio
import logging
import random
import time

from app.devices.base import BaseScanner

log = logging.getLogger("satori.scanner")

STX, ETX = b"\x02", b"\x03"

# Scanner thường nối-gửi-rồi-ngắt sau mỗi lần quét. Coi là "đang kết nối" nếu
# vừa có hoạt động (kết nối hoặc đọc mã) trong khoảng này → trạng thái xanh ổn
# định khi băng tải chạy, chỉ đỏ khi scanner im lặng thật lâu (mất kết nối).
SCANNER_GRACE_SEC = 30.0


# ── REAL: Datalogic Matrix qua TCP ──
class RealScanner(BaseScanner):
    """KẾT NỐI TỚI scanner TCP (scanner đóng vai SERVER, vd Datalogic Matrix ở
    10.1.1.126:51236). App là client: mở kết nối, đọc frame STX+data+ETX, gọi
    on_scan(ma). Tự kết nối lại nếu rớt.

    Để hỗ trợ nhiều scanner, DeviceManager tạo nhiều RealScanner cùng on_scan.
    """

    def __init__(self, on_scan, host, port):
        super().__init__(on_scan)
        self.host, self.port = host, port
        self._running = False
        self._connected = False
        self._writer = None
        self._last_seen = 0.0  # monotonic lần cuối nối/đọc mã

    async def start(self):
        self._running = True
        while self._running:
            try:
                reader, writer = await asyncio.open_connection(
                    self.host, self.port)
                self._writer = writer
                self._connected = True
                self._last_seen = time.monotonic()
                log.info("RealScanner đã kết nối tới scanner %s:%s",
                         self.host, self.port)
                await self._read_loop(reader)
            except (OSError, asyncio.TimeoutError) as e:
                log.warning("RealScanner không kết nối được %s:%s (%s) — thử lại 3s",
                            self.host, self.port, e)
            finally:
                self._connected = False
                if self._writer:
                    try:
                        self._writer.close()
                    except Exception:
                        pass
                    self._writer = None
            if self._running:
                await asyncio.sleep(3)   # chờ rồi kết nối lại

    async def _read_loop(self, reader):
        buf = b""
        while self._running:
            chunk = await reader.read(512)
            if not chunk:          # scanner đóng kết nối
                log.info("Scanner %s:%s ngắt kết nối", self.host, self.port)
                break
            self._last_seen = time.monotonic()
            buf += chunk
            # Chấp nhận cả ETX (0x03) lẫn xuống dòng (\n) làm dấu kết thúc frame.
            # Scanner Datalogic Foenix ở nhà máy gói kiểu: STX + data + \r\n.
            while True:
                idx_n = buf.find(b"\n")
                idx_e = buf.find(ETX)
                ends = [i for i in (idx_n, idx_e) if i != -1]
                if not ends:
                    break
                end = min(ends)
                frame = buf[:end]
                buf = buf[end + 1:]
                # Bỏ STX/ETX/CR/khoảng trắng ở hai đầu
                ma = frame.strip(b"\x02\x03\r\n \t").decode(errors="ignore").strip()
                if ma:
                    await self.on_scan(ma)

    async def stop(self):
        self._running = False
        if self._writer:
            try:
                self._writer.close()
            except Exception:
                pass

    async def is_connected(self) -> bool:
        # OK khi đang giữ kết nối, HOẶC vừa có dữ liệu trong SCANNER_GRACE_SEC
        # (phòng scanner ngắt-nối từng lúc).
        if self._connected:
            return True
        return (time.monotonic() - self._last_seen) < SCANNER_GRACE_SEC


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
