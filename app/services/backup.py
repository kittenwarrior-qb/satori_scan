"""Sao lưu DB tự động.

An toàn cho SQLite kể cả khi đang ghi nhờ dùng SQLite Backup API (không copy
file thô — copy thô có thể hỏng nếu đúng lúc đang ghi). Chạy nền theo chu kỳ
`backup_interval_hours`, giữ lại `backup_keep` bản mới nhất.

Postgres: KHÔNG backup trong app — nên dùng `pg_dump` qua Task Scheduler.
"""
import asyncio
import logging
import os
import sqlite3
from datetime import datetime

from app.config import settings

log = logging.getLogger("satori.backup")


def _sqlite_path() -> str | None:
    """Đường dẫn file SQLite từ DATABASE_URL, hoặc None nếu không phải SQLite."""
    url = settings.database_url
    if not url.startswith("sqlite"):
        return None
    return url.split("sqlite:///", 1)[-1]


def backup_now() -> str | None:
    """Tạo 1 bản sao lưu ngay. Trả đường dẫn file backup, hoặc None nếu bỏ qua."""
    src = _sqlite_path()
    if src is None:
        log.warning("Sao lưu tự động chỉ hỗ trợ SQLite. Postgres dùng pg_dump.")
        return None
    if not os.path.exists(src):
        log.warning("Chưa có file DB để sao lưu: %s", src)
        return None

    os.makedirs(settings.backup_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(settings.backup_dir, f"satori_{stamp}.db")

    src_conn = sqlite3.connect(src)
    dst_conn = sqlite3.connect(dest)
    try:
        with dst_conn:
            src_conn.backup(dst_conn)   # SQLite Backup API — an toàn
    finally:
        src_conn.close()
        dst_conn.close()

    _prune()
    log.info("Đã sao lưu DB -> %s", dest)
    return dest


def _prune() -> None:
    """Giữ N bản mới nhất, xóa bản cũ hơn."""
    keep = max(1, settings.backup_keep)
    try:
        files = sorted(
            (f for f in os.listdir(settings.backup_dir)
             if f.startswith("satori_") and f.endswith(".db")),
            reverse=True,
        )
    except FileNotFoundError:
        return
    for old in files[keep:]:
        try:
            os.remove(os.path.join(settings.backup_dir, old))
        except OSError:
            pass


async def backup_loop() -> None:
    """Vòng lặp nền: sao lưu ngay khi khởi động rồi lặp mỗi chu kỳ."""
    interval = max(0.1, settings.backup_interval_hours) * 3600
    while True:
        try:
            backup_now()
        except Exception:
            log.exception("Lỗi sao lưu DB")
        await asyncio.sleep(interval)
