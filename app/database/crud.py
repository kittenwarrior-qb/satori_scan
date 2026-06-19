"""Hàm thêm/sửa/đọc dữ liệu dùng chung."""
from datetime import datetime, date as date_type

from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from app.database import models


# ── SupplierBatch ──
def get_supplier_batch(db: Session, sup_id: int):
    return db.get(models.SupplierBatch, sup_id)


def list_supplier_batches(db: Session):
    return (db.query(models.SupplierBatch)
            .order_by(models.SupplierBatch.id.desc()).all())


def create_supplier_batch(db: Session, nha_cung_cap: str, so_lo_ncc: str,
                          so_luong_chai: int, so_lan_tai_su_dung: int):
    s = models.SupplierBatch(
        nha_cung_cap=nha_cung_cap,
        so_lo_ncc=so_lo_ncc,
        so_luong_chai=so_luong_chai,
        so_lan_tai_su_dung=so_lan_tai_su_dung,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def update_supplier_batch(db: Session, sup_id: int, **kwargs):
    s = db.get(models.SupplierBatch, sup_id)
    if not s:
        return None
    for k, v in kwargs.items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s


def create_production_batch(db: Session, supplier_batch_id: int,
                            so_lo_san_xuat: str, ngay_san_xuat: date_type):
    b = models.ProductionBatch(
        supplier_batch_id=supplier_batch_id,
        so_lo_san_xuat=so_lo_san_xuat,
        ngay_san_xuat=ngay_san_xuat,
        counter=0,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def update_production_batch(db: Session, batch_id: int, **kwargs):
    b = db.get(models.ProductionBatch, batch_id)
    if not b:
        return None
    for k, v in kwargs.items():
        setattr(b, k, v)
    db.commit()
    db.refresh(b)
    return b


# ── ProductionBatch ──
def get_production_batch(db: Session, batch_id: int):
    return db.get(models.ProductionBatch, batch_id)


def get_production_by_lo(db: Session, so_lo_san_xuat: str):
    return (
        db.query(models.ProductionBatch)
        .filter(models.ProductionBatch.so_lo_san_xuat == so_lo_san_xuat)
        .first()
    )


def list_production_batches(db: Session):
    return (
        db.query(models.ProductionBatch)
        .order_by(models.ProductionBatch.id.desc())
        .all()
    )


# ── Bottle ──
def get_bottle_by_ma(db: Session, ma_chai: str):
    return (
        db.query(models.Bottle)
        .filter(models.Bottle.ma_chai == ma_chai)
        .first()
    )


def create_bottle(db: Session, **kwargs):
    bottle = models.Bottle(**kwargs)
    db.add(bottle)
    db.commit()
    db.refresh(bottle)
    return bottle


def increment_reuse(db: Session, bottle: models.Bottle):
    bottle.so_lan_thuc_te += 1
    bottle.trang_thai = bottle.so_lan_thuc_te
    db.commit()
    db.refresh(bottle)
    return bottle


def count_bottles_in_batch(db: Session, batch_id: int) -> int:
    return (
        db.query(models.Bottle)
        .filter(models.Bottle.production_batch_id == batch_id)
        .count()
    )


# ── Session ──
def get_active_session(db: Session, che_do: str = None):
    q = db.query(models.Session).filter(models.Session.ket_thuc.is_(None))
    if che_do:
        q = q.filter(models.Session.che_do == che_do)
    return q.order_by(models.Session.id.desc()).first()


def get_session(db: Session, session_id: int):
    return db.get(models.Session, session_id)


def start_session(db: Session, che_do: str, production_batch_id: int,
                  operator: str = "operator"):
    s = models.Session(
        che_do=che_do,
        production_batch_id=production_batch_id,
        operator=operator,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def end_session(db: Session, session: models.Session):
    session.ket_thuc = datetime.now()
    db.commit()


def bump_session(db: Session, session_id: int, ok: bool):
    # Atomic SQL update — tránh lost-update khi 2 luồng đọc-ghi đồng thời.
    col = models.Session.tong_hop_le if ok else models.Session.tong_loi
    db.execute(
        sa_update(models.Session)
        .where(models.Session.id == session_id)
        .values({col.key: col + 1})
    )
    db.commit()


# ── ScanEvent ──
def log_event(db: Session, **kwargs):
    e = models.ScanEvent(**kwargs)
    db.add(e)
    db.commit()
    return e
