"""Test nạp dữ liệu CodeIT từ Excel: tạo lô + chai, idempotent, ánh xạ cột."""
from datetime import date

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.database import models
import import_codeit


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _make_xlsx(path):
    wb = Workbook()
    ws = wb.active
    # Header đúng như CodeIT xuất (Figure 11)
    ws.append(["Số lô sản xuất", "Ngày sản xuất", "Số lô nhà cung cấp",
               "Mã số chai", "Trạng thái chai", "Số lần tái sử dụng"])
    ws.append(["STR200108P1", "08/01/2020", "NN2001008Q1", "20010800001", 1, 1])
    ws.append(["STR200108P1", "08/01/2020", "NN2001008Q1", "20010800002", -3, 1])
    ws.append(["STR200108P1", "08/01/2020", "NN2001008Q1", "20010800003", 0, 0])
    wb.save(path)


def test_import_creates_batches_and_bottles(tmp_path, db):
    f = tmp_path / "STR200108P1.xlsx"
    _make_xlsx(f)

    st = import_codeit.import_file(db, str(f), default_tsd=5)
    assert st["chai_moi"] == 3
    assert st["lo_ncc_moi"] == 1
    assert st["lo_sx_moi"] == 1

    # Lô NCC tạo với giới hạn TSD mặc định = 5
    sup = db.query(models.SupplierBatch).filter_by(so_lo_ncc="NN2001008Q1").first()
    assert sup.so_lan_tai_su_dung == 5

    # Chai bị loại giữ đúng trạng thái -3 + số lần dùng thực tế
    b = db.query(models.Bottle).filter_by(ma_chai="20010800002").first()
    assert b.trang_thai == -3
    assert b.so_lan_thuc_te == 1
    assert b.ngay_san_xuat == date(2020, 1, 8)


def test_import_idempotent(tmp_path, db):
    f = tmp_path / "STR200108P1.xlsx"
    _make_xlsx(f)
    import_codeit.import_file(db, str(f))
    st2 = import_codeit.import_file(db, str(f))   # chạy lại
    assert st2["chai_moi"] == 0
    assert st2["chai_bo_qua"] == 3
    assert db.query(models.Bottle).count() == 3   # không nhân đôi
