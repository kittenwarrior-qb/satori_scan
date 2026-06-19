"""Xuất báo cáo Excel (tương thích format CodeIT cũ) + báo cáo theo ca/ngày."""
import os
from datetime import datetime, time, timedelta

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import models

REPORT_DIR = os.path.join("data", "reports")

CHE_DO_LABEL = {
    "DINH_DANH": "Định danh",
    "PHAN_LOAI": "Phân loại",
    "LOAI_BO":   "Loại bỏ",
}

_HEADER_FILL = PatternFill("solid", fgColor="1E293B")
_HEADER_FONT = Font(bold=True, color="FFFFFF")


def _style_header(ws, ncols: int):
    for col in range(1, ncols + 1):
        c = ws.cell(row=1, column=col)
        c.fill = _HEADER_FILL
        c.font = _HEADER_FONT
        c.alignment = Alignment(horizontal="center")


def shift_summary(db: Session, from_date=None, to_date=None,
                  che_do: str | None = None) -> dict:
    """Tổng hợp theo CA (mỗi phiên sản xuất) trong khoảng ngày.

    Trả về từng ca + thống kê hợp lệ/lỗi/tỉ lệ + phân tích nguyên nhân lỗi.
    """
    q = db.query(models.Session)
    if from_date:
        q = q.filter(models.Session.bat_dau >= datetime.combine(from_date, time.min))
    if to_date:
        q = q.filter(models.Session.bat_dau
                     < datetime.combine(to_date + timedelta(days=1), time.min))
    if che_do:
        q = q.filter(models.Session.che_do == che_do)
    sessions = q.order_by(models.Session.bat_dau.desc()).all()

    # Phân tích nguyên nhân lỗi: gom scan_events theo (session, ket_qua) 1 lần.
    bd: dict[int, dict[str, int]] = {}
    ids = [s.id for s in sessions]
    if ids:
        rows = (db.query(models.ScanEvent.session_id, models.ScanEvent.ket_qua,
                         func.count())
                .filter(models.ScanEvent.session_id.in_(ids))
                .group_by(models.ScanEvent.session_id, models.ScanEvent.ket_qua))
        for sid, kq, cnt in rows:
            bd.setdefault(sid, {})[kq] = cnt

    out_rows, tot_ok, tot_err = [], 0, 0
    for s in sessions:
        ok = s.tong_hop_le or 0
        err = s.tong_loi or 0
        tong = ok + err
        tot_ok += ok
        tot_err += err
        out_rows.append({
            "session_id": s.id,
            "ngay": s.bat_dau.strftime("%d/%m/%Y") if s.bat_dau else "",
            "che_do": s.che_do,
            "che_do_label": CHE_DO_LABEL.get(s.che_do, s.che_do),
            "operator": s.operator or "",
            "bat_dau": s.bat_dau.strftime("%H:%M") if s.bat_dau else "",
            "ket_thuc": s.ket_thuc.strftime("%H:%M") if s.ket_thuc else "—",
            "tong_hop_le": ok,
            "tong_loi": err,
            "tong": tong,
            "ty_le_loi": round(err / tong * 100, 1) if tong else 0,
            "breakdown": bd.get(s.id, {}),
        })

    tong_all = tot_ok + tot_err
    return {
        "rows": out_rows,
        "totals": {
            "tong_hop_le": tot_ok, "tong_loi": tot_err, "tong": tong_all,
            "ty_le_loi": round(tot_err / tong_all * 100, 1) if tong_all else 0,
        },
    }


def export_shifts(db: Session, from_date=None, to_date=None,
                  che_do: str | None = None) -> str:
    """Xuất báo cáo theo ca ra data/reports/ShiftReport.xlsx."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    data = shift_summary(db, from_date, to_date, che_do)
    wb = Workbook()
    ws = wb.active
    ws.title = "Báo cáo theo ca"
    headers = ["Ngày", "Ca", "Trưởng ca", "Bắt đầu", "Kết thúc",
               "Hợp lệ", "Lỗi", "Tổng", "Tỉ lệ lỗi (%)",
               "Quá hạn", "Không đọc", "Mã lạ", "Loại thủ công"]
    ws.append(headers)
    _style_header(ws, len(headers))
    for r in data["rows"]:
        b = r["breakdown"]
        ws.append([
            r["ngay"], r["che_do_label"], r["operator"], r["bat_dau"],
            r["ket_thuc"], r["tong_hop_le"], r["tong_loi"], r["tong"],
            r["ty_le_loi"], b.get("OVER_LIMIT", 0), b.get("NOREAD", 0),
            b.get("UNKNOWN", 0), b.get("REJECTED", 0),
        ])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 13
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(REPORT_DIR, f"ShiftReport_{stamp}.xlsx")
    wb.save(path)
    return path


def export_production_report(db: Session) -> str:
    """Tổng hợp tất cả lô SX -> data/reports/ProductionReport.xlsx."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Báo cáo sản xuất"

    # Cột khớp đúng báo cáo CodeIT (Figure 10 trong User Manual):
    # Số lô sản xuất | Số lô nhà cung cấp | Số lượng chai | Ngày sản xuất
    headers = ["Số lô sản xuất", "Số lô nhà cung cấp", "Số lượng chai",
               "Ngày sản xuất"]
    ws.append(headers)
    _style_header(ws, len(headers))

    for b in db.query(models.ProductionBatch).order_by(
            models.ProductionBatch.id).all():
        sup = b.supplier_batch
        sl = (db.query(models.Bottle)
              .filter(models.Bottle.production_batch_id == b.id).count())
        ws.append([
            b.so_lo_san_xuat,
            sup.so_lo_ncc if sup else "",
            sl,
            b.ngay_san_xuat.strftime("%d/%m/%Y") if b.ngay_san_xuat else "",
        ])

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 16

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(REPORT_DIR, f"ProductionReport_{stamp}.xlsx")
    wb.save(path)
    return path


def export_batch_detail(db: Session, so_lo_san_xuat: str) -> str | None:
    """Chi tiết chai theo 1 lô SX -> data/reports/<SoLoSX>.xlsx."""
    batch = (db.query(models.ProductionBatch)
             .filter(models.ProductionBatch.so_lo_san_xuat == so_lo_san_xuat)
             .first())
    if batch is None:
        return None

    os.makedirs(REPORT_DIR, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = so_lo_san_xuat[:31]

    # Cột khớp đúng báo cáo chi tiết CodeIT (Figure 11 trong User Manual):
    # Số lô SX | Ngày SX | Số lô NCC | Mã số chai | Trạng thái chai | Số lần TSD
    headers = ["Số lô sản xuất", "Ngày sản xuất", "Số lô nhà cung cấp",
               "Mã số chai", "Trạng thái chai", "Số lần tái sử dụng"]
    ws.append(headers)
    _style_header(ws, len(headers))

    sup = batch.supplier_batch
    for bot in (db.query(models.Bottle)
                .filter(models.Bottle.production_batch_id == batch.id)
                .order_by(models.Bottle.id).all()):
        ws.append([
            batch.so_lo_san_xuat,
            bot.ngay_san_xuat.strftime("%d/%m/%Y") if bot.ngay_san_xuat else "",
            sup.so_lo_ncc if sup else "",
            bot.ma_chai,
            bot.trang_thai,
            bot.so_lan_thuc_te,
        ])

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 16

    safe = "".join(c for c in so_lo_san_xuat if c.isalnum() or c in "-_")
    path = os.path.join(REPORT_DIR, f"{safe}.xlsx")
    wb.save(path)
    return path
