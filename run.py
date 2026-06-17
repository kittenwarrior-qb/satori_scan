"""Điểm khởi động khi đóng gói .exe — chạy server + mở kiosk fullscreen."""
import os
import subprocess
import threading
import time
import webbrowser

import uvicorn

from app.config import settings


def start_server():
    uvicorn.run(
        "app.main:app",
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
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    browser = next((p for p in chrome_paths if os.path.exists(p)), None)
    if browser:
        subprocess.Popen([
            browser,
            "--kiosk",
            f"--app={url}",
            "--window-size=1024,768",   # khớp độ phân giải màn hình công nghiệp
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
