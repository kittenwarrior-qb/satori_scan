"""API cho QUẢN LÝ & BÁO CÁO — tra cứu, truy vết, xuất Excel."""
import os
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import models
from app.database.connection import get_db
from app.services import report as report_svc

router = APIRouter()


def _parse_date(s: Optional[str]):
    """Parse 'YYYY-MM-DD' (từ ô <input type=date>). None nếu rỗng/sai."""
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


@router.get("/reports/batches")
def batches(db: Session = Depends(get_db)):
    """Bảng tổng hợp tất cả lô SX."""
    out = []
    for b in (db.query(models.ProductionBatch)
              .order_by(models.ProductionBatch.id.desc()).all()):
        sup = b.supplier_batch
        sl = (db.query(models.Bottle)
              .filter(models.Bottle.production_batch_id == b.id).count())
        out.append({
            "so_lo_san_xuat": b.so_lo_san_xuat,
            "ngay_san_xuat": b.ngay_san_xuat.strftime("%d/%m/%Y")
            if b.ngay_san_xuat else "",
            "so_luong_chai": sl,
            "ncc_lo": sup.so_lo_ncc if sup else "",
            "ncc_tsd": sup.so_lan_tai_su_dung if sup else "",
            "ncc_sl": sup.so_luong_chai if sup else "",
        })
    return out


@router.get("/reports/search")
def search(q: str, field: str = "ma_chai", db: Session = Depends(get_db)):
    """Tìm theo Lô SX / Lô NCC / Mã chai. field: lo_sx|lo_ncc|ma_chai."""
    q = q.strip()
    query = (db.query(models.Bottle)
             .join(models.ProductionBatch,
                   models.Bottle.production_batch_id == models.ProductionBatch.id)
             .join(models.SupplierBatch,
                   models.Bottle.supplier_batch_id == models.SupplierBatch.id))

    if field == "lo_sx":
        query = query.filter(models.ProductionBatch.so_lo_san_xuat.like(f"%{q}%"))
    elif field == "lo_ncc":
        query = query.filter(models.SupplierBatch.so_lo_ncc.like(f"%{q}%"))
    else:
        query = query.filter(models.Bottle.ma_chai.like(f"%{q}%"))

    out = []
    for bot in query.order_by(models.Bottle.id).limit(2000).all():
        out.append({
            "lo_sx": bot.production_batch.so_lo_san_xuat
            if bot.production_batch else "",
            "lo_ncc": bot.supplier_batch.so_lo_ncc if bot.supplier_batch else "",
            "ma_chai": bot.ma_chai,
            "so_lan_thuc_te": bot.so_lan_thuc_te,
            "trang_thai": bot.trang_thai,
            "ngay_san_xuat": bot.ngay_san_xuat.strftime("%d/%m/%Y")
            if bot.ngay_san_xuat else "",
        })
    return {"count": len(out), "rows": out}


@router.get("/reports/shifts")
def shifts(from_date: Optional[str] = None, to_date: Optional[str] = None,
           che_do: Optional[str] = None, db: Session = Depends(get_db)):
    """Báo cáo theo ca/ngày trong khoảng thời gian."""
    return report_svc.shift_summary(db, _parse_date(from_date),
                                    _parse_date(to_date), che_do)


@router.post("/reports/export/shifts")
def export_shifts(from_date: Optional[str] = None, to_date: Optional[str] = None,
                  che_do: Optional[str] = None, db: Session = Depends(get_db)):
    path = report_svc.export_shifts(db, _parse_date(from_date),
                                    _parse_date(to_date), che_do)
    return {"path": path, "filename": os.path.basename(path)}


@router.get("/reports/trace")
def trace(ma_chai: str, db: Session = Depends(get_db)):
    """Truy vết toàn bộ lịch sử quét của 1 chai."""
    events = (db.query(models.ScanEvent)
              .filter(models.ScanEvent.ma_chai == ma_chai.strip())
              .order_by(models.ScanEvent.id).all())
    return [{
        "event_type": e.event_type,
        "ket_qua": e.ket_qua,
        "scanned_at": e.scanned_at.strftime("%d/%m/%Y %H:%M:%S")
        if e.scanned_at else "",
    } for e in events]


@router.post("/reports/export/production")
def export_production(db: Session = Depends(get_db)):
    path = report_svc.export_production_report(db)
    return {"path": path, "filename": os.path.basename(path)}


@router.post("/reports/export/batch")
def export_batch(so_lo_san_xuat: str, db: Session = Depends(get_db)):
    path = report_svc.export_batch_detail(db, so_lo_san_xuat.strip())
    if path is None:
        raise HTTPException(404, "Không tìm thấy lô SX")
    return {"path": path, "filename": os.path.basename(path)}


@router.post("/reports/backup")
def backup():
    """Sao lưu DB ngay lập tức (an toàn cho SQLite)."""
    from app.services.backup import backup_now
    path = backup_now()
    if not path:
        raise HTTPException(400, "Sao lưu tự động chỉ hỗ trợ SQLite "
                                 "(Postgres dùng pg_dump bên ngoài).")
    return {"path": path, "filename": os.path.basename(path)}


@router.get("/reports/download")
def download(filename: str):
    """Tải file Excel đã xuất."""
    safe = os.path.basename(filename)
    path = os.path.join(report_svc.REPORT_DIR, safe)
    if not os.path.exists(path):
        raise HTTPException(404, "File không tồn tại")
    return FileResponse(
        path, filename=safe,
        media_type="application/vnd.openxmlformats-officedocument."
                   "spreadsheetml.sheet")
