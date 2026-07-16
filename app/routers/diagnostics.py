"""Chẩn đoán IO-Box tại hiện trường — thử trực tiếp slave id / địa chỉ coil /
cách ghi (FC5 đơn lẻ hay FC15 nhiều coil) mà KHÔNG cần sửa .env hay khởi động
lại satori.exe. Mục đích: dò ra đúng thông số ModBus thật của tủ điện ngay tại
nhà máy, xong rồi mới lưu vào .env — không phải sửa code tại chỗ.

Mỗi request ở đây tự mở 1 kết nối ModBus TCP RIÊNG, dùng xong đóng ngay — không
đụng tới device_manager.iobox đang phục vụ sản xuất, nên không ảnh hưởng ca
đang chạy (nếu có).
"""
import logging
import os
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

log = logging.getLogger("satori.diag")

router = APIRouter()

# Chỉ cho phép sửa các khoá này qua "Lưu vào .env" — không mở rộng thành công
# cụ chỉnh sửa file tuỳ ý.
_ALLOWED_ENV_KEYS = {
    "IOBOX_HOST", "IOBOX_PORT", "IOBOX_SLAVE_ID", "IOBOX_WRITE_MODE",
    "IOBOX_COIL_BANG_TAI", "IOBOX_COIL_DAY_LOAI", "IOBOX_PULSE_WIDTH",
}


@router.get("/diag/iobox/defaults")
def defaults():
    """Giá trị đang cấu hình trong .env — để màn hình chẩn đoán điền sẵn."""
    return {
        "host": settings.iobox_host,
        "port": settings.iobox_port,
        "slave_id": settings.iobox_slave_id,
        "coil_bang_tai": settings.iobox_coil_bang_tai,
        "coil_day_loai": settings.iobox_coil_day_loai,
        "pulse_width": settings.iobox_pulse_width,
    }


async def _open_client(host: str, port: int):
    from pymodbus.client import AsyncModbusTcpClient
    client = AsyncModbusTcpClient(host, port=port)
    ok = await client.connect()
    if not (ok and client.connected):
        raise HTTPException(503, f"Không kết nối được TCP tới {host}:{port}")
    return client


class WriteCoilIn(BaseModel):
    host: str
    port: int
    address: int
    value: bool
    slave: int = 1
    multi: bool = False  # False = Write Single Coil (0x05), True = Write Multiple Coils (0x0F)


@router.post("/diag/iobox/write-coil")
async def write_coil(body: WriteCoilIn):
    """Thử ghi 1 coil và trả về kết quả THẬT (không nuốt lỗi)."""
    method = ("write_coils (FC 0x0F — Write Multiple Coils)" if body.multi
              else "write_coil (FC 0x05 — Write Single Coil)")
    client = await _open_client(body.host, body.port)
    try:
        if body.multi:
            result = await client.write_coils(body.address, [body.value], slave=body.slave)
        else:
            result = await client.write_coil(body.address, body.value, slave=body.slave)
    except Exception as e:
        return {"ok": False, "method": method,
                "message": f"Lỗi kết nối/giao thức: {e}"}
    finally:
        client.close()

    if result.isError():
        return {"ok": False, "method": method,
                "message": f"PLC TỪ CHỐI lệnh: {result}"}
    return {"ok": True, "method": method,
            "message": f"PLC CHẤP NHẬN lệnh ghi coil {body.address} = {body.value} "
                       f"(slave {body.slave})"}


class PulseIn(BaseModel):
    host: str
    port: int
    address: int
    slave: int = 1
    pulse_width: float = 0.3
    multi: bool = False


@router.post("/diag/iobox/pulse")
async def pulse(body: PulseIn):
    """Mô phỏng ĐÚNG hành vi day_loai_chai() thật: bật -> giữ -> tắt.
    Dùng để test xy-lanh đẩy loại có bung ra thật hay không."""
    client = await _open_client(body.host, body.port)
    try:
        ok, msg = await _pulse_once(client, body.address, body.slave, body.multi,
                                    body.pulse_width)
        return {"ok": ok, "message": msg}
    except Exception as e:
        return {"ok": False, "message": f"Lỗi kết nối/giao thức: {e}"}
    finally:
        client.close()


async def _pulse_once(client, address: int, slave: int, multi: bool, pulse_width: float):
    """Bật -> giữ -> tắt 1 coil, dùng chung cho pulse() và auto-scan()."""
    write = client.write_coils if multi else client.write_coil
    val_on = [True] if multi else True
    val_off = [False] if multi else False

    r1 = await write(address, val_on, slave=slave)
    if r1.isError():
        return False, f"Bị từ chối ngay khi BẬT: {r1}"

    import asyncio
    await asyncio.sleep(pulse_width)

    r2 = await write(address, val_off, slave=slave)
    if r2.isError():
        return False, f"BẬT được nhưng bị từ chối khi TẮT: {r2} — coil có thể đang GIỮ BẬT!"
    return True, "PLC chấp nhận cả lệnh bật và tắt."


class AutoScanIn(BaseModel):
    host: str
    port: int
    address: int
    pulse_width: float = 0.3


@router.post("/diag/iobox/auto-scan")
async def auto_scan(body: AutoScanIn):
    """Tự động thử lần lượt các tổ hợp slave id (0/1) x cách ghi (đơn/nhiều)
    — người dùng không cần biết ModBus là gì, chỉ cần đọc kết quả cuối và
    quan sát xy-lanh. Mỗi tổ hợp đều bấm xung BẬT-TẮT thật để dễ quan sát.
    """
    import asyncio

    combos = [
        {"slave": 1, "multi": False, "label": "Cách 1"},
        {"slave": 0, "multi": False, "label": "Cách 2"},
        {"slave": 1, "multi": True,  "label": "Cách 3"},
        {"slave": 0, "multi": True,  "label": "Cách 4"},
    ]
    client = await _open_client(body.host, body.port)
    results = []
    try:
        for c in combos:
            ok, msg = await _pulse_once(client, body.address, c["slave"], c["multi"],
                                        body.pulse_width)
            results.append({
                "label": c["label"], "slave": c["slave"], "multi": c["multi"],
                "ok": ok, "message": msg,
            })
            await asyncio.sleep(1.0)  # nghỉ giữa các lần để quan sát/tránh dồn xung
    except Exception as e:
        results.append({"label": "Lỗi", "ok": False, "message": f"Lỗi kết nối/giao thức: {e}"})
    finally:
        client.close()
    return {"results": results}


class ReadStatusIn(BaseModel):
    host: str
    port: int


@router.post("/diag/iobox/probe")
async def probe(body: ReadStatusIn):
    """Chỉ kiểm tra kết nối TCP thuần — chưa gửi lệnh ModBus nào."""
    try:
        client = await _open_client(body.host, body.port)
        client.close()
        return {"ok": True, "message": f"Kết nối TCP tới {body.host}:{body.port} thành công."}
    except HTTPException as e:
        return {"ok": False, "message": e.detail}


def _write_env_key(key: str, value: str):
    key = key.strip().upper()
    if key not in _ALLOWED_ENV_KEYS:
        raise HTTPException(400, f"Không được phép sửa khoá '{key}' từ trang chẩn đoán")

    env_path = ".env"
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    for i, line in enumerate(lines):
        if pattern.match(line):
            lines[i] = f"{key}={value}\n"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    log.info("Đã lưu %s=%s vào .env qua trang chẩn đoán", key, value)


class SaveEnvIn(BaseModel):
    key: str
    value: str


@router.post("/diag/save-env")
def save_env(body: SaveEnvIn):
    """Ghi 1 dòng KEY=VALUE vào .env — chỉ cho phép các khoá IO-Box đã duyệt
    sẵn, tránh trở thành công cụ ghi file tuỳ ý."""
    _write_env_key(body.key, body.value)
    return {"ok": True, "message": f"Đã lưu {body.key.upper()}={body.value} vào .env — "
                                   f"khởi động lại satori.exe để áp dụng."}


class SaveComboIn(BaseModel):
    slave: int
    multi: bool


@router.post("/diag/save-combo")
def save_combo(body: SaveComboIn):
    """Lưu 1 phát cả Slave ID lẫn cách ghi (đơn/nhiều) — dùng khi người vận
    hành xác nhận 1 tổ hợp từ auto-scan hoạt động thật (xy-lanh đã bung)."""
    _write_env_key("IOBOX_SLAVE_ID", str(body.slave))
    _write_env_key("IOBOX_WRITE_MODE", "multi" if body.multi else "single")
    return {"ok": True, "message": "Đã lưu tổ hợp này vào .env — "
                                   "khởi động lại satori.exe để áp dụng cho sản xuất thật."}
