"""Điểm khởi động khi đóng gói .exe — chạy server + mở kiosk fullscreen."""
import os
import subprocess
import threading
import time
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
