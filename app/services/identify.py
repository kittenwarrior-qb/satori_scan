"""Logic ĐỊNH DANH chai mới — sinh mã, in laser, lưu DB."""
import logging
from datetime import date

from sqlalchemy import update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import crud, models
from app.devices.manager import device_manager
from app.services.ma_chai import generate_ma_chai

log = logging.getLogger("satori.identify")


def _next_counter_for_date(db: Session, ngay_sx: date) -> int:
    """Counter kế tiếp DUY NHẤT theo NGÀY SX (mọi lô cùng ngày dùng chung dãy).

    Tránh trùng mã khi 2 lô sản xuất chạy cùng một ngày: thay vì đếm theo từng
    lô, ta dựa trên mã chai lớn nhất đã tồn tại cho ngày đó. Mã chai cố định 11
    ký tự (yyMMdd + 5 số) nên so sánh chuỗi tương đương so sánh số.
    """
    prefix = ngay_sx.strftime("%y%m%d")
    last = (db.query(models.Bottle.ma_chai)
            .filter(models.Bottle.ma_chai.like(prefix + "%"))
            .order_by(models.Bottle.ma_chai.desc())
            .first())
    if last and last[0][6:].isdigit():
        return int(last[0][6:]) + 1
    return 1


async def identify_new_bottle(db: Session, production_batch_id: int,
                              session_id: int) -> dict:
    """In mã cho 1 chai mới: sinh mã (duy nhất theo ngày) -> lưu DB -> in laser."""
    batch = db.get(models.ProductionBatch, production_batch_id)
    if batch is None:
        return {"ket_qua": "ERROR", "message": "Lô SX không tồn tại"}

    # 1. Sinh mã + GIỮ CHỖ trong DB trước khi in. Nếu mã vừa bị chai khác
    #    chiếm (in tay + scanner tự động cùng lúc) → IntegrityError → thử số kế.
    bottle = None
    ma_chai = None
    for _ in range(50):
        counter = _next_counter_for_date(db, batch.ngay_san_xuat)
        ma_chai = generate_ma_chai(batch.ngay_san_xuat, counter)
        try:
            bottle = crud.create_bottle(
                db,
                ma_chai=ma_chai,
                production_batch_id=batch.id,
                supplier_batch_id=batch.supplier_batch_id,
                so_lan_thuc_te=0,
                trang_thai=0,
                ngay_san_xuat=batch.ngay_san_xuat,
            )
            break
        except IntegrityError:
            db.rollback()
    if bottle is None:
        log.error("Không sinh được mã duy nhất cho lô %s", batch.so_lo_san_xuat)
        return {"ket_qua": "ERROR", "message": "Không sinh được mã duy nhất"}

    # 2. Bộ đếm lô — atomic để tránh lost-update khi in tay + scanner đồng thời.
    db.execute(
        sa_update(models.ProductionBatch)
        .where(models.ProductionBatch.id == batch.id)
        .values(counter=models.ProductionBatch.counter + 1)
    )
    db.commit()
    db.refresh(batch)

    # 3. In laser SAU khi đã giữ chỗ mã → mã in ra chắc chắn có trong DB.
    try:
        await device_manager.laser.print_code(ma_chai)
    except Exception as laser_err:
        log.error("Laser thất bại khi in '%s': %s", ma_chai, laser_err)
        crud.log_event(db, bottle_id=bottle.id, ma_chai=ma_chai,
                       event_type="PRINT", ket_qua="FAILED", session_id=session_id)
        return {
            "ket_qua": "PRINT_FAILED", "ma_chai": ma_chai,
            "message": "Máy laser lỗi — cần in lại mã này",
        }

    # 4. Log + thống kê
    crud.log_event(db, bottle_id=bottle.id, ma_chai=ma_chai,
                   event_type="PRINT", ket_qua="OK", session_id=session_id)
    crud.bump_session(db, session_id, ok=True)

    return {"ket_qua": "OK", "ma_chai": ma_chai, "counter": batch.counter}
