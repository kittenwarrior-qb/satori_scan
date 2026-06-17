"""Nạp dữ liệu mẫu (lô NCC, lô SX, vài chai). Chạy: python seed.py"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from datetime import date

from app.database.connection import SessionLocal
from app.database import models
from app.services.ma_chai import generate_ma_chai


def main():
    db = SessionLocal()

    if db.query(models.SupplierBatch).first():
        print("Đã có dữ liệu — bỏ qua seed.")
        db.close()
        return

    # Lô NCC mẫu
    sup = models.SupplierBatch(
        nha_cung_cap="Ngọc Nghĩa",
        so_lo_ncc="NN2001008Q1",
        so_luong_chai=700,
        so_lan_tai_su_dung=5,
    )
    db.add(sup)
    db.commit()
    db.refresh(sup)

    # Lô SX mẫu
    ngay = date(2020, 1, 8)
    prod = models.ProductionBatch(
        supplier_batch_id=sup.id,
        so_lo_san_xuat="STR200108P1",
        ngay_san_xuat=ngay,
        counter=10,
    )
    db.add(prod)
    db.commit()
    db.refresh(prod)

    # Vài chai mẫu để test phân loại (counter 1..10)
    for i in range(1, 11):
        ma = generate_ma_chai(ngay, i)
        db.add(models.Bottle(
            ma_chai=ma,
            production_batch_id=prod.id,
            supplier_batch_id=sup.id,
            so_lan_thuc_te=0 if i <= 7 else 5,  # 8,9,10 đã đủ giới hạn → sẽ bị loại
            trang_thai=0 if i <= 7 else 5,
            ngay_san_xuat=ngay,
        ))
    db.commit()

    print(f"Đã tạo lô NCC #{sup.id} ({sup.so_lo_ncc}), "
          f"lô SX #{prod.id} ({prod.so_lo_san_xuat}), 10 chai mẫu.")
    print("Mã chai mẫu: 20010800001 .. 20010800010 "
          "(00008-00010 đã đủ 5 lần → sẽ bị loại khi phân loại).")
    db.close()


if __name__ == "__main__":
    main()
