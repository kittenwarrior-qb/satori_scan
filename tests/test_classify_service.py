"""Test logic phân loại đầy đủ với DB SQLite in-memory + IO-Box giả."""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.database import models
from app.devices.manager import device_manager
from app.devices.iobox import MockIOBox
from app.services import classify as classify_svc


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    s = SessionLocal()

    sup = models.SupplierBatch(so_lo_ncc="NN1", so_luong_chai=100,
                               so_lan_tai_su_dung=3)
    s.add(sup); s.commit()
    prod = models.ProductionBatch(supplier_batch_id=sup.id, so_lo_san_xuat="P1",
                                  ngay_san_xuat=date(2020, 1, 8), counter=0)
    s.add(prod); s.commit()
    # chai 1: còn dùng được; chai 2: đã đủ giới hạn
    s.add(models.Bottle(ma_chai="20010800001", production_batch_id=prod.id,
                        supplier_batch_id=sup.id, so_lan_thuc_te=0, trang_thai=0,
                        ngay_san_xuat=date(2020, 1, 8)))
    s.add(models.Bottle(ma_chai="20010800002", production_batch_id=prod.id,
                        supplier_batch_id=sup.id, so_lan_thuc_te=3, trang_thai=3,
                        ngay_san_xuat=date(2020, 1, 8)))
    s.add(models.Session(che_do="PHAN_LOAI", production_batch_id=prod.id))
    s.commit()
    yield s
    s.close()


@pytest.fixture(autouse=True)
def fake_iobox():
    device_manager.iobox = MockIOBox()
    classify_svc._last_seen.clear()   # reset chống-quét-trùng giữa các test


@pytest.mark.asyncio
async def test_ok_increments(db):
    r = await classify_svc.classify_bottle(db, "20010800001", 1)
    assert r["ket_qua"] == "OK"
    assert r["so_lan_thuc_te"] == 1


@pytest.mark.asyncio
async def test_over_limit(db):
    r = await classify_svc.classify_bottle(db, "20010800002", 1)
    assert r["ket_qua"] == "OVER_LIMIT"
    # Chai quá hạn được đánh dấu trạng thái âm = -1 (quá hạn TSD)
    b = classify_svc.crud.get_bottle_by_ma(db, "20010800002")
    assert b.trang_thai == -1


def test_reject_manual_marks_minus3(db):
    from app.services import reject as reject_svc
    r = reject_svc.reject_bottle(db, "20010800001", 1)
    assert r["ket_qua"] == "REJECTED"
    b = classify_svc.crud.get_bottle_by_ma(db, "20010800001")
    assert b.trang_thai == -3   # -3 = loại thủ công (cảm quan)


@pytest.mark.asyncio
async def test_unknown(db):
    r = await classify_svc.classify_bottle(db, "29991200001", 1)
    assert r["ket_qua"] == "UNKNOWN"


@pytest.mark.asyncio
async def test_noread(db):
    r = await classify_svc.classify_bottle(db, "NOREAD", 1)
    assert r["ket_qua"] == "NOREAD"


@pytest.mark.asyncio
async def test_bad_format(db):
    r = await classify_svc.classify_bottle(db, "12", 1)
    assert r["ket_qua"] == "NOREAD"


@pytest.mark.asyncio
async def test_ok_khong_co_iobox_fault(db):
    """Chai OK không đẩy loại nên không bao giờ báo lỗi IO-Box."""
    r = await classify_svc.classify_bottle(db, "20010800001", 1)
    assert r.get("iobox_fault") is None  # OK path không gắn cờ


@pytest.mark.asyncio
async def test_iobox_loi_van_loai_va_bao_co(db):
    """IO-Box lỗi khi đẩy chai quá hạn: vẫn đánh dấu loại + gắn cờ iobox_fault."""
    class BrokenIOBox(MockIOBox):
        async def day_loai_chai(self):
            raise RuntimeError("ModBus mất kết nối")
    device_manager.iobox = BrokenIOBox()

    r = await classify_svc.classify_bottle(db, "20010800002", 1)
    assert r["ket_qua"] == "OVER_LIMIT"
    assert r["iobox_fault"] is True
    # Dù IO-Box lỗi, chai vẫn được đánh dấu loại trong DB
    b = classify_svc.crud.get_bottle_by_ma(db, "20010800002")
    assert b.trang_thai == -1


@pytest.mark.asyncio
async def test_quet_trung_khong_tang_dem(db):
    """Quét cùng 1 mã 2 lần liên tiếp: lần 2 là DUPLICATE, TSD không tăng tiếp."""
    r1 = await classify_svc.classify_bottle(db, "20010800001", 1)
    assert r1["ket_qua"] == "OK"
    assert r1["so_lan_thuc_te"] == 1

    r2 = await classify_svc.classify_bottle(db, "20010800001", 1)
    assert r2["ket_qua"] == "DUPLICATE"

    # TSD thực tế vẫn = 1 (không bị cộng nhầm thành 2)
    bottle = classify_svc.crud.get_bottle_by_ma(db, "20010800001")
    assert bottle.so_lan_thuc_te == 1
