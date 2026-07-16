"""API quản lý lô NCC / lô SX + xác thực mật khẩu admin."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import crud
from app.database.connection import get_db

router = APIRouter()


# ── Xác thực mật khẩu ──────────────────────────────────────────────────────
# Nhận mật khẩu qua BODY (JSON), KHÔNG qua query string — query string bị
# uvicorn ghi nguyên văn vào access log console mỗi request (vd:
# "POST /api/verify-password?password=stradmin HTTP/1.1"), tức mật khẩu thật
# hiện rõ trong cửa sổ console mà quy trình vận hành yêu cầu luôn mở.

class PasswordIn(BaseModel):
    password: str


@router.post("/verify-password")
def verify_password(body: PasswordIn):
    if body.password != settings.admin_password:
        raise HTTPException(403, "Mật khẩu không đúng")
    return {"ok": True}


# ── Lô NCC ─────────────────────────────────────────────────────────────────

class SupplierBatchIn(BaseModel):
    nha_cung_cap: str
    so_lo_ncc: str
    so_luong_chai: int
    so_lan_tai_su_dung: int


@router.get("/batches/supplier")
def list_supplier(db: Session = Depends(get_db)):
    rows = crud.list_supplier_batches(db)
    return [
        {
            "id": r.id,
            "nha_cung_cap": r.nha_cung_cap,
            "so_lo_ncc": r.so_lo_ncc,
            "so_luong_chai": r.so_luong_chai,
            "so_lan_tai_su_dung": r.so_lan_tai_su_dung,
        }
        for r in rows
    ]


@router.post("/batches/supplier")
def create_supplier(body: SupplierBatchIn, db: Session = Depends(get_db)):
    try:
        s = crud.create_supplier_batch(
            db,
            nha_cung_cap=body.nha_cung_cap,
            so_lo_ncc=body.so_lo_ncc,
            so_luong_chai=body.so_luong_chai,
            so_lan_tai_su_dung=body.so_lan_tai_su_dung,
        )
        return {"id": s.id, "so_lo_ncc": s.so_lo_ncc}
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            400, f"Số lô nhà cung cấp '{body.so_lo_ncc}' đã tồn tại, "
                 f"vui lòng nhập số lô khác")
    except Exception:
        db.rollback()
        raise HTTPException(400, "Không thể lưu dữ liệu, vui lòng thử lại")


@router.put("/batches/supplier/{sup_id}")
def update_supplier(sup_id: int, body: SupplierBatchIn,
                    db: Session = Depends(get_db)):
    try:
        s = crud.update_supplier_batch(
            db, sup_id,
            nha_cung_cap=body.nha_cung_cap,
            so_lo_ncc=body.so_lo_ncc,
            so_luong_chai=body.so_luong_chai,
            so_lan_tai_su_dung=body.so_lan_tai_su_dung,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            400, f"Số lô nhà cung cấp '{body.so_lo_ncc}' đã tồn tại, "
                 f"vui lòng nhập số lô khác")
    except Exception:
        db.rollback()
        raise HTTPException(400, "Không thể lưu dữ liệu, vui lòng thử lại")
    if not s:
        raise HTTPException(404, "Không tìm thấy lô NCC")
    return {"id": s.id, "so_lo_ncc": s.so_lo_ncc}


# ── Lô SX ──────────────────────────────────────────────────────────────────

class ProductionBatchIn(BaseModel):
    supplier_batch_id: int
    so_lo_san_xuat: str
    ngay_san_xuat: date


@router.post("/batches/production")
def create_production(body: ProductionBatchIn, db: Session = Depends(get_db)):
    # Kiểm tra lô NCC tồn tại
    sup = crud.get_supplier_batch(db, body.supplier_batch_id)
    if not sup:
        raise HTTPException(404, "Lô NCC không tồn tại")
    try:
        b = crud.create_production_batch(
            db,
            supplier_batch_id=body.supplier_batch_id,
            so_lo_san_xuat=body.so_lo_san_xuat,
            ngay_san_xuat=body.ngay_san_xuat,
        )
        return {
            "id": b.id, "so_lo_san_xuat": b.so_lo_san_xuat,
            "ngay_san_xuat": b.ngay_san_xuat.strftime("%d/%m/%Y"),
        }
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            400, f"Số lô sản xuất '{body.so_lo_san_xuat}' đã tồn tại, "
                 f"vui lòng nhập số lô khác")
    except Exception:
        db.rollback()
        raise HTTPException(400, "Không thể lưu dữ liệu, vui lòng thử lại")


@router.put("/batches/production/{batch_id}")
def update_production(batch_id: int, body: ProductionBatchIn,
                      db: Session = Depends(get_db)):
    try:
        b = crud.update_production_batch(
            db, batch_id,
            supplier_batch_id=body.supplier_batch_id,
            so_lo_san_xuat=body.so_lo_san_xuat,
            ngay_san_xuat=body.ngay_san_xuat,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            400, f"Số lô sản xuất '{body.so_lo_san_xuat}' đã tồn tại, "
                 f"vui lòng nhập số lô khác")
    except Exception:
        db.rollback()
        raise HTTPException(400, "Không thể lưu dữ liệu, vui lòng thử lại")
    if not b:
        raise HTTPException(404, "Không tìm thấy lô SX")
    return {
        "id": b.id, "so_lo_san_xuat": b.so_lo_san_xuat,
        "ngay_san_xuat": b.ngay_san_xuat.strftime("%d/%m/%Y"),
    }
