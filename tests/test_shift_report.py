"""Test báo cáo theo ca: tổng hợp, tỉ lệ lỗi, phân tích nguyên nhân, lọc ngày."""
from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.database import models
from app.services import report as report_svc


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    sess = models.Session(che_do="PHAN_LOAI", operator="Ca A",
                          tong_hop_le=8, tong_loi=2,
                          bat_dau=datetime(2020, 1, 8, 7, 0),
                          ket_thuc=datetime(2020, 1, 8, 15, 0))
    s.add(sess); s.commit()
    for kq in ["OK"] * 8 + ["OVER_LIMIT", "NOREAD"]:
        s.add(models.ScanEvent(ma_chai="x", event_type="SCAN",
                               ket_qua=kq, session_id=sess.id))
    s.commit()
    yield s
    s.close()


def test_shift_summary(db):
    d = report_svc.shift_summary(db)
    assert len(d["rows"]) == 1
    r = d["rows"][0]
    assert r["tong_hop_le"] == 8 and r["tong_loi"] == 2
    assert r["ty_le_loi"] == 20.0
    assert r["che_do_label"] == "Phân loại"
    assert r["breakdown"]["OVER_LIMIT"] == 1
    assert r["breakdown"]["NOREAD"] == 1
    assert d["totals"]["ty_le_loi"] == 20.0


def test_shift_date_filter_excludes(db):
    d = report_svc.shift_summary(db, from_date=date(2021, 1, 1),
                                 to_date=date(2021, 1, 31))
    assert len(d["rows"]) == 0


def test_shift_date_filter_includes(db):
    d = report_svc.shift_summary(db, from_date=date(2020, 1, 8),
                                 to_date=date(2020, 1, 8))
    assert len(d["rows"]) == 1   # ngày 'đến' bao gồm cả ngày đó
