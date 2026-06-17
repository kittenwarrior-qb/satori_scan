"""Tạo các bảng DB. Chạy: python init_db.py"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.database.connection import Base, engine
from app.database import models  # noqa: F401 — import để đăng ký models


def main():
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)
    print("Đang tạo các bảng...")
    Base.metadata.create_all(bind=engine)
    print("Xong! Các bảng đã được tạo.")


if __name__ == "__main__":
    main()
