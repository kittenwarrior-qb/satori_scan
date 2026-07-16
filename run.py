"""Điểm khởi động khi đóng gói .exe — chạy server + mở kiosk fullscreen."""
import glob
import os
import subprocess
import tempfile
import threading
import time
import uuid
import webbrowser

import uvicorn

from app.config import settings
from app.main import app as fastapi_app


def start_server():
    uvicorn.run(
        fastapi_app,
        host="127.0.0.1",
        port=settings.web_port,
        log_level="info",
    )


def _fresh_profile_dir() -> str:
    """Thư mục profile Chrome/Edge MỚI TINH cho mỗi lần chạy — không có
    cache cũ từ trước, nên mỗi lần đổi bản .exe, kiosk luôn tải đúng bản
    JS/CSS mới nhất mà không cần xoá cache tay. Dọn profile của các lần
    chạy trước (best-effort) để không tích rác trong thư mục temp."""
    base = os.path.join(tempfile.gettempdir(), "satori_kiosk")
    for old in glob.glob(base + "_*"):
        try:
            import shutil
            shutil.rmtree(old, ignore_errors=True)
        except Exception:
            pass
    profile = f"{base}_{uuid.uuid4().hex[:8]}"
    os.makedirs(profile, exist_ok=True)
    return profile


def open_kiosk():
    time.sleep(2)  # đợi server lên
    url = f"http://127.0.0.1:{settings.web_port}"
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    browser = next((p for p in chrome_paths if os.path.exists(p)), None)
    if browser:
        # --app: cửa sổ sạch (không tab, không thanh địa chỉ) NHƯNG vẫn còn
        # khung cửa sổ có nút X để chạm tay đóng — quan trọng với máy cảm ứng
        # không có bàn phím. (Muốn khóa cứng toàn màn hình sau này thì thêm
        # lại "--kiosk", nhưng lúc đó phải có cách thoát khác.)
        subprocess.Popen([
            browser,
            f"--app={url}",
            f"--user-data-dir={_fresh_profile_dir()}",  # profile mới -> không cache cũ
            "--no-first-run",
            "--start-maximized",        # phóng to gần kín màn hình
            "--force-device-scale-factor=1",  # không để Chrome tự zoom
            "--disable-pinch",          # tắt zoom cảm ứng
            "--overscroll-history-navigation=0",
        ])
    else:
        webbrowser.open(url)


if __name__ == "__main__":
    # Đảm bảo thư mục data tồn tại khi chạy .exe
    os.makedirs("data/reports", exist_ok=True)
    threading.Thread(target=open_kiosk, daemon=True).start()
    start_server()
