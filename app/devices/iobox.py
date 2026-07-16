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
        self.slave_id      = settings.iobox_slave_id
        self.use_multi     = settings.iobox_write_mode.strip().lower() == "multi"

    async def connect(self):
        await self.client.connect()
        log.info("RealIOBox connect %s:%s -> %s (slave=%s coil_bang_tai=%s coil_day_loai=%s)",
                 self.host, self.port, self.client.connected,
                 self.slave_id, self.coil_bang_tai, self.coil_day_loai)

    async def _write_coil(self, address: int, value: bool, label: str) -> bool:
        """Ghi 1 coil + KIỂM TRA phản hồi.

        pymodbus KHÔNG raise exception khi PLC từ chối lệnh (vd sai địa chỉ
        coil, sai slave id) — nó trả về 1 response object có .isError() =
        True. Code cũ bỏ qua hoàn toàn giá trị trả về, nên TCP vẫn báo "đã
        kết nối" trong khi coil thực tế không hề đổi — PLC lặng lẽ từ chối.
        Đây là nguyên nhân phổ biến nhất của "kết nối được nhưng không đẩy
        loại": sai coil address (off-by-one) hoặc sai slave/unit id.
        """
        try:
            if self.use_multi:
                result = await self.client.write_coils(address, [value], slave=self.slave_id)
            else:
                result = await self.client.write_coil(address, value, slave=self.slave_id)
        except Exception as e:
            log.error("Ghi coil %s (%s, slave=%s) LỖI kết nối: %s",
                      address, label, self.slave_id, e)
            return False
        if result.isError():
            log.error(
                "Ghi coil %s (%s, slave=%s) bị PLC TỪ CHỐI: %s — kiểm tra lại "
                "IOBOX_COIL_* và IOBOX_SLAVE_ID trong .env so với bảng I/O "
                "thật của tủ điện (rất hay lệch do đánh số coil 0-based vs "
                "1-based, hoặc sai slave/unit id).",
                address, label, self.slave_id, result)
            return False
        return True

    async def start_bang_tai(self):
        if not await self._write_coil(self.coil_bang_tai, True, "băng tải BẬT"):
            raise RuntimeError(
                f"PLC từ chối lệnh bật băng tải (coil {self.coil_bang_tai}, "
                f"slave {self.slave_id}) — xem log để biết chi tiết")

    async def stop_bang_tai(self):
        if not await self._write_coil(self.coil_bang_tai, False, "băng tải TẮT"):
            raise RuntimeError(
                f"PLC từ chối lệnh tắt băng tải (coil {self.coil_bang_tai}, "
                f"slave {self.slave_id}) — xem log để biết chi tiết")

    async def day_loai_chai(self):
        # Không raise ở đây: nếu PLC từ chối, ta VẪN phải lưu đúng trạng thái
        # chai + ghi log audit ở lớp classify — chỉ cảnh báo thật to trong
        # console để người vận hành biết cần kiểm tra tay, không để mất luôn
        # cả bản ghi vì lỗi phần cứng.
        ok1 = await self._write_coil(self.coil_day_loai, True, "đẩy loại BẬT")
        await asyncio.sleep(self.pulse_width)
        ok2 = await self._write_coil(self.coil_day_loai, False, "đẩy loại TẮT")
        if not (ok1 and ok2):
            log.error("*** ĐẨY LOẠI CÓ THỂ ĐÃ THẤT BẠI — chai vừa quét có thể "
                      "CHƯA bị đẩy ra khỏi băng tải, cần kiểm tra tay. ***")

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
