"""Xuất báo cáo Excel (tương thích format CodeIT cũ)."""
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy.orm import Session

from app.database import models

REPORT_DIR = os.path.join("data", "reports")

_HEADER_FILL = PatternFill("solid", fgColor="1E293B")
_HEADER_FONT = Font(bold=True, color="FFFFFF")


def _style_header(ws, ncols: int):
    for col in range(1, ncols + 1):
        c = ws.cell(row=1, column=col)
        c.fill = _HEADER_FILL
        c.font = _HEADER_FONT
        c.alignment = Alignment(horizontal="center")


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

    path = os.path.join(REPORT_DIR, "ProductionReport.xlsx")
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
