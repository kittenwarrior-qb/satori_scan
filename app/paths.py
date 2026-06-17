"""Đường dẫn tài nguyên — đúng cả khi chạy dev lẫn .exe (PyInstaller)."""
import os
import sys


def resource_path(rel: str) -> str:
    """Trả đường dẫn tuyệt đối tới tài nguyên (templates/static)."""
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel)


TEMPLATES_DIR = resource_path("app/templates")
STATIC_DIR = resource_path("app/static")
