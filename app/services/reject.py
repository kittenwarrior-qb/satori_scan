"""Logic LOẠI BỎ chai (nhập tay / quét cầm tay)."""
import logging

from sqlalchemy.orm import Session

from app.database import crud

log = logging.getLogger("satori.reject")


def reject_bottle(db: Session, ma_chai: str, session_id: int) -> dict:
    """Đánh dấu chai không đạt (trang_thai âm)."""
    bottle = crud.get_bottle_by_ma(db, ma_chai)
    if bottle is None:
        crud.log_event(db, bottle_id=None, ma_chai=ma_chai,
                       event_type="REJECT", ket_qua="UNKNOWN",
                       session_id=session_id)
        return {"ket_qua": "UNKNOWN", "ma_chai": ma_chai}

    # Đã bị loại trước đó → vẫn ghi log (audit) nhưng KHÔNG đếm lỗi lần 2.
    if bottle.trang_thai is not None and bottle.trang_thai < 0:
        crud.log_event(db, bottle_id=bottle.id, ma_chai=ma_chai,
                       event_type="REJECT", ket_qua="REJECTED",
                       session_id=session_id)
        return {"ket_qua": "REJECTED", "ma_chai": ma_chai, "already": True}

    bottle.trang_thai = -1  # âm = đã loại
    db.commit()

    crud.log_event(db, bottle_id=bottle.id, ma_chai=ma_chai,
                   event_type="REJECT", ket_qua="REJECTED",
                   session_id=session_id)
    crud.bump_session(db, session_id, ok=False)
    return {"ket_qua": "REJECTED", "ma_chai": ma_chai}
