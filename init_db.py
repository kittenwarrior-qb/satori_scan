"""Tạo các bảng DB. Chạy: python init_db.py"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.database.connection import Base, engine
from app.database import models  # noqa: F401 — import để đăng ký models


# Index cho hiệu năng khi dữ liệu lớn (hàng trăm nghìn → triệu dòng).
# Dùng CREATE INDEX IF NOT EXISTS để chạy được cả trên DB đã có sẵn dữ liệu.
_INDEXES = [
    ("ix_scan_events_ma_chai",          "scan_events",       "ma_chai"),
    ("ix_scan_events_session_id",       "scan_events",       "session_id"),
    ("ix_scan_events_scanned_at",       "scan_events",       "scanned_at"),
    ("ix_bottles_production_batch_id",  "bottles",           "production_batch_id"),
    ("ix_bottles_supplier_batch_id",    "bottles",           "supplier_batch_id"),
    ("ix_sessions_bat_dau",             "sessions",          "bat_dau"),
]


def ensure_indexes():
    """Tạo index nếu chưa có — an toàn để chạy lại nhiều lần."""
    with engine.begin() as conn:
        for name, table, col in _INDEXES:
            conn.exec_driver_sql(
                f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({col})")


def main():
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)
    print("Đang tạo các bảng...")
    Base.metadata.create_all(bind=engine)
    print("Đang tạo index...")
    ensure_indexes()
    print("Xong! Các bảng + index đã sẵn sàng.")


if __name__ == "__main__":
    main()
