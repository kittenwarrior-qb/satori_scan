"""Logic ĐỊNH DANH chai mới — sinh mã, in laser, lưu DB."""
import logging

from sqlalchemy.orm import Session

from app.database import crud, models
from app.devices.manager import device_manager
from app.services.ma_chai import generate_ma_chai

log = logging.getLogger("satori.identify")


async def identify_new_bottle(db: Session, production_batch_id: int,
                              session_id: int) -> dict:
    """In mã cho 1 chai mới: sinh mã -> in laser -> lưu DB."""
    batch = db.get(models.ProductionBatch, production_batch_id)
    if batch is None:
        return {"ket_qua": "ERROR", "message": "Lô SX không tồn tại"}

    # 1. Tăng counter, sinh mã
    batch.counter += 1
    ma_chai = generate_ma_chai(batch.ngay_san_xuat, batch.counter)
    db.commit()

    # 2. In laser (mock = log)
    await device_manager.laser.print_code(ma_chai)

    # 3. Lưu chai
    bottle = crud.create_bottle(
        db,
        ma_chai=ma_chai,
        production_batch_id=batch.id,
        supplier_batch_id=batch.supplier_batch_id,
        so_lan_thuc_te=0,
        trang_thai=0,
        ngay_san_xuat=batch.ngay_san_xuat,
    )

    # 4. Log + thống kê
    crud.log_event(db, bottle_id=bottle.id, ma_chai=ma_chai,
                   event_type="PRINT", ket_qua="OK", session_id=session_id)
    crud.bump_session(db, session_id, ok=True)

    return {"ket_qua": "OK", "ma_chai": ma_chai, "counter": batch.counter}
