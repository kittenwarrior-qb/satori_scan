"""Test định danh: mã chai DUY NHẤT kể cả 2 lô SX cùng ngày sản xuất."""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.database import models
from app.devices.manager import device_manager
from app.devices.laser import MockLaser
from app.services import identify as identify_svc


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    s = SessionLocal()

    sup = models.SupplierBatch(so_lo_ncc="NN1", so_luong_chai=100,
                               so_lan_tai_su_dung=5)
    s.add(sup); s.commit()
    # Hai lô SX KHÁC NHAU nhưng CÙNG NGÀY 08/01/2020
    for lo in ("P1", "P2"):
        s.add(models.ProductionBatch(supplier_batch_id=sup.id, so_lo_san_xuat=lo,
                                     ngay_san_xuat=date(2020, 1, 8), counter=0))
    s.add(models.Session(che_do="DINH_DANH", production_batch_id=1))
    s.commit()
    yield s
    s.close()


@pytest.fixture(autouse=True)
def fake_laser():
    device_manager.laser = MockLaser()


@pytest.mark.asyncio
async def test_ma_chai_duy_nhat_2_lo_cung_ngay(db):
    """In xen kẽ giữa 2 lô cùng ngày → mọi mã phải khác nhau, tăng dần."""
    seen = set()
    for batch_id in (1, 2, 1, 2, 1):
        r = await identify_svc.identify_new_bottle(db, batch_id, 1)
        assert r["ket_qua"] == "OK"
        assert r["ma_chai"] not in seen, f"Trùng mã: {r['ma_chai']}"
        seen.add(r["ma_chai"])

    # 5 chai → counter chung của ngày = 00001..00005
    assert seen == {
        "20010800001", "20010800002", "20010800003",
        "20010800004", "20010800005",
    }
    # Tổng số chai trong DB = 5, không vi phạm UNIQUE
    assert db.query(models.Bottle).count() == 5
