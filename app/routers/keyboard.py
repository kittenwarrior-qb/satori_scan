"""Bật/tắt bàn phím ảo gốc của Windows (osk.exe).

Server chạy ngay trên máy kiosk (kể cả Windows 7), nên có thể subprocess
mở/đóng bàn phím ảo hệ thống thay vì tự build 1 bộ bàn phím ảo bằng JS.
Trên môi trường không phải Windows (dev/CI), lệnh không tồn tại → log + trả
lỗi nhẹ nhàng, không làm crash app.
"""
import logging
import platform
import subprocess

from fastapi import APIRouter

log = logging.getLogger("satori.keyboard")

router = APIRouter()


@router.post("/keyboard/open")
def open_keyboard():
    if platform.system() != "Windows":
        log.info("Bàn phím ảo: bỏ qua (không phải Windows)")
        return {"ok": False, "message": "Chỉ hỗ trợ trên Windows"}
    try:
        # osk.exe gọi trực tiếp từ 1 tiến trình chưa được Windows tin cậy
        # (vd python.exe) sẽ bị chặn với WinError 740 (yêu cầu elevation) vì
        # osk.exe chỉ nằm trong danh sách auto-elevate khi được khởi chạy bởi
        # 1 tiến trình shell tin cậy. Gọi qua explorer.exe để né việc này —
        # không cần quyền admin, không hiện UAC prompt (đã kiểm chứng thực tế).
        subprocess.Popen(["explorer.exe", r"C:\Windows\System32\osk.exe"])
        return {"ok": True}
    except Exception as e:
        log.warning("Không mở được bàn phím ảo: %s", e)
        return {"ok": False, "message": str(e)}


@router.post("/keyboard/close")
def close_keyboard():
    if platform.system() != "Windows":
        return {"ok": False, "message": "Chỉ hỗ trợ trên Windows"}
    try:
        subprocess.run(["taskkill", "/IM", "osk.exe", "/F"],
                       capture_output=True, timeout=5)
        return {"ok": True}
    except Exception as e:
        log.warning("Không đóng được bàn phím ảo: %s", e)
        return {"ok": False, "message": str(e)}
