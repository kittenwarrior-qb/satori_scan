"""Test sao lưu DB SQLite (dùng Backup API, prune giữ N bản)."""
import os
import sqlite3

from app.config import settings
from app.services import backup


def _make_db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()


def test_backup_now(tmp_path, monkeypatch):
    db = tmp_path / "satori.db"
    _make_db(db)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db}")
    monkeypatch.setattr(settings, "backup_dir", str(tmp_path / "backups"))

    dest = backup.backup_now()
    assert dest and os.path.exists(dest)
    # Bản backup đọc được và có dữ liệu
    c = sqlite3.connect(dest)
    assert c.execute("SELECT x FROM t").fetchone()[0] == 1
    c.close()


def test_backup_prune_keeps_n(tmp_path, monkeypatch):
    db = tmp_path / "satori.db"
    _make_db(db)
    bdir = tmp_path / "backups"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db}")
    monkeypatch.setattr(settings, "backup_dir", str(bdir))
    monkeypatch.setattr(settings, "backup_keep", 3)

    # Tạo sẵn 5 file backup giả với tên tăng dần
    bdir.mkdir()
    for name in ("satori_20200101_000001.db", "satori_20200101_000002.db",
                 "satori_20200101_000003.db", "satori_20200101_000004.db"):
        (bdir / name).write_text("x")

    backup.backup_now()   # thêm 1 bản thật -> tổng 5, prune còn 3
    remaining = [f for f in os.listdir(bdir) if f.endswith(".db")]
    assert len(remaining) == 3


def test_backup_skips_non_sqlite(monkeypatch):
    monkeypatch.setattr(settings, "database_url",
                        "postgresql://u:p@localhost/db")
    assert backup.backup_now() is None
