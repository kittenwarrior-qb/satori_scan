"""Import dữ liệu lịch sử CodeIT (các file ProductionReport*.xlsx) vào satori.db.

Chạy trên máy DEV (có sẵn các file Excel), tạo ra 1 file satori.db đầy đủ,
rồi copy file đó vào data\\ trên máy PLC.

  python scripts/import_codeit.py <thư_mục_chứa_xlsx> <file_db_đích>

Ví dụ:
  python scripts/import_codeit.py "D:/Desktop/dl_matrix/Reports" "dist/satori_imported.db"

Quy ước (theo lựa chọn của người dùng):
  - BỎ QUA dòng NoRead / mã rỗng (chỉ import chai có mã thật).
  - Mỗi mã chai = 1 dòng trong bảng bottles, giữ TRẠNG THÁI MỚI NHẤT
    (so sánh theo thời gian Ngày sản xuất).
"""
import glob
import io
import os
import sys
from datetime import date, datetime

import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Cho phép import app.* khi chạy từ thư mục gốc dự án
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database.connection import Base          # noqa: E402
from app.database import models                    # noqa: E402,F401

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

LOG = io.open("import_log.txt", "w", encoding="utf-8")


def log(msg):
    try:
        print(msg)
    except Exception:
        print(str(msg).encode("ascii", "replace").decode("ascii"))
    LOG.write(str(msg) + "\n")
    LOG.flush()


def parse_ts(val):
    """Trả datetime từ ô Ngày sản xuất (datetime hoặc chuỗi M/D/YYYY ...)."""
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day)
    s = str(val).strip()
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S",
                "%m/%d/%Y", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def to_int(val):
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return 0


def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else r"D:\Desktop\dl_matrix\Reports"
    db_path = sys.argv[2] if len(sys.argv) > 2 else "dist/satori_imported.db"

    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)

    files = sorted(glob.glob(os.path.join(src_dir, "*.xlsx")))
    log(f"Tìm thấy {len(files)} file .xlsx trong {src_dir}")

    # ── Cấu trúc gom dữ liệu trong bộ nhớ ──
    suppliers = {}      # so_lo_ncc -> max_reuse
    prod_batches = {}   # so_lo_sx  -> {"ncc": so_lo_ncc, "ngay": date}
    bottles = {}        # ma_chai   -> {reuse, status, sx, ncc, ngay, ts}

    rows_seen = 0
    rows_skipped_noread = 0
    files_used = 0

    for fi, path in enumerate(files, 1):
        try:
            wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        except Exception as e:
            log(f"  [BỎ] {os.path.basename(path)}: lỗi mở ({e})")
            continue
        ws = wb.active
        it = ws.iter_rows(values_only=True)
        try:
            header = next(it)
        except StopIteration:
            wb.close()
            continue
        # Chỉ nhận file chi tiết (có cột "Mã số chai")
        if len(header) < 6 or header[2] != "Mã số chai":
            wb.close()
            continue
        files_used += 1

        for row in it:
            if len(row) < 6:
                continue
            rows_seen += 1
            so_lo_sx = (str(row[0]).strip() if row[0] is not None else "")
            so_lo_ncc = (str(row[1]).strip() if row[1] is not None else "")
            ma_chai = (str(row[2]).strip() if row[2] is not None else "")
            reuse = to_int(row[3])
            status = (str(row[4]).strip() if row[4] is not None else "")
            ts = parse_ts(row[5])

            # Bỏ NoRead / mã rỗng / không có lô SX
            if not ma_chai or ma_chai.upper() == "NOREAD" or not so_lo_sx:
                rows_skipped_noread += 1
                continue

            ngay = ts.date() if ts else None

            # Supplier: theo dõi reuse lớn nhất để đặt giới hạn an toàn
            if so_lo_ncc:
                suppliers[so_lo_ncc] = max(suppliers.get(so_lo_ncc, 0), reuse)

            # Production batch: ghi nhận NCC + ngày (lần đầu thấy)
            pb = prod_batches.get(so_lo_sx)
            if pb is None:
                prod_batches[so_lo_sx] = {"ncc": so_lo_ncc or None,
                                          "ngay": ngay}
            else:
                if pb["ncc"] is None and so_lo_ncc:
                    pb["ncc"] = so_lo_ncc
                if pb["ngay"] is None and ngay:
                    pb["ngay"] = ngay

            # Bottle: giữ bản ghi MỚI NHẤT theo ts
            b = bottles.get(ma_chai)
            ts_cmp = ts or datetime.min
            if b is None or ts_cmp > b["ts"]:
                bottles[ma_chai] = {
                    "reuse": reuse, "status": status,
                    "sx": so_lo_sx, "ncc": so_lo_ncc or None,
                    "ngay": ngay, "ts": ts_cmp,
                }
        wb.close()
        if fi % 20 == 0:
            log(f"  ...đã đọc {fi}/{len(files)} file, "
                f"{len(bottles)} chai, {rows_seen} dòng")

    log(f"\nĐọc xong: {files_used} file chi tiết, {rows_seen} dòng, "
        f"bỏ {rows_skipped_noread} dòng NoRead/rỗng.")
    log(f"  Suppliers: {len(suppliers)} | Lô SX: {len(prod_batches)} | "
        f"Chai: {len(bottles)}")

    # ── Tạo DB đích + bảng ──
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # File Excel KHÔNG chứa "số lần cho phép tái sử dụng" của lô → đặt mặc định.
    # 10 theo chính sách nhà máy (chỉnh lại từng lô qua "Cập nhật lô NCC" nếu cần,
    # hoặc kéo giới hạn thật từ DB gốc 10.1.1.106).
    DEFAULT_LIMIT = 10
    FALLBACK_DATE = date(2020, 1, 1)

    # 1) Suppliers
    sup_id = {}
    sup_rows = []
    for i, (ncc, max_reuse) in enumerate(suppliers.items(), 1):
        sup_id[ncc] = i
        sup_rows.append({
            "id": i, "nha_cung_cap": "Ngọc Nghĩa", "so_lo_ncc": ncc,
            "so_luong_chai": 0,
            "so_lan_tai_su_dung": max(DEFAULT_LIMIT, max_reuse),
        })
    db.bulk_insert_mappings(models.SupplierBatch, sup_rows)

    # 2) Production batches
    pb_id = {}
    pb_rows = []
    for i, (sx, info) in enumerate(prod_batches.items(), 1):
        pb_id[sx] = i
        pb_rows.append({
            "id": i, "so_lo_san_xuat": sx,
            "ngay_san_xuat": info["ngay"] or FALLBACK_DATE,
            "supplier_batch_id": sup_id.get(info["ncc"]) if info["ncc"] else None,
            "counter": 0,
        })
    db.bulk_insert_mappings(models.ProductionBatch, pb_rows)

    # 3) Bottles
    REJECT = models.REJECT_OVER_LIMIT   # -1: dùng cho "Bị lỗi" có mã thật
    bot_rows = []
    n_ok = n_err = 0
    for i, (ma, b) in enumerate(bottles.items(), 1):
        if b["status"].lower().startswith("h"):     # "Hợp lệ"
            trang_thai = b["reuse"]
            n_ok += 1
        else:                                       # "Bị lỗi"
            trang_thai = REJECT
            n_err += 1
        bot_rows.append({
            "id": i, "ma_chai": ma,
            "production_batch_id": pb_id.get(b["sx"]),
            "supplier_batch_id": sup_id.get(b["ncc"]) if b["ncc"] else None,
            "so_lan_thuc_te": b["reuse"], "trang_thai": trang_thai,
            "ngay_san_xuat": b["ngay"],
        })
        if len(bot_rows) >= 10000:
            db.bulk_insert_mappings(models.Bottle, bot_rows)
            bot_rows = []
    if bot_rows:
        db.bulk_insert_mappings(models.Bottle, bot_rows)

    db.commit()

    # 4) Index cho tốc độ tra cứu
    with engine.begin() as conn:
        for name, table, col in [
            ("ix_bottles_ma_chai", "bottles", "ma_chai"),
            ("ix_bottles_production_batch_id", "bottles", "production_batch_id"),
            ("ix_bottles_supplier_batch_id", "bottles", "supplier_batch_id"),
        ]:
            conn.exec_driver_sql(
                f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({col})")

    db.close()
    log(f"\n=== XONG ===")
    log(f"  File DB: {os.path.abspath(db_path)}")
    log(f"  Suppliers: {len(sup_rows)}")
    log(f"  Lô sản xuất: {len(pb_rows)}")
    log(f"  Chai: {len(bottles)}  (Hợp lệ: {n_ok}, Bị lỗi: {n_err})")
    LOG.close()


if __name__ == "__main__":
    main()
