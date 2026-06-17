"""Logic PHÂN LOẠI chai — trái tim hệ thống. Quyết định OK hay loại."""
import logging

from sqlalchemy.orm import Session

from app.database import crud, models
from app.devices.manager import device_manager
from app.services.ma_chai import parse_ma_chai

log = logging.getLogger("satori.classify")


async def classify_bottle(db: Session, ma_chai: str, session_id: int) -> dict:
    """Xử lý 1 lần quét. Tự gọi đẩy loại nếu cần. Trả về kết quả."""
    # 1. NoRead (scanner báo không đọc được / chuỗi rỗng)
    if not ma_chai or ma_chai == "NOREAD":
        await device_manager.iobox.day_loai_chai()
        _log(db, None, ma_chai or "", "NOREAD", session_id)
        crud.bump_session(db, session_id, ok=False)
        return {"ket_qua": "NOREAD", "ma_chai": None}

    # 2. Format sai → coi như không đọc được
    if parse_ma_chai(ma_chai) is None:
        await device_manager.iobox.day_loai_chai()
        _log(db, None, ma_chai, "NOREAD", session_id)
        crud.bump_session(db, session_id, ok=False)
        return {"ket_qua": "NOREAD", "ma_chai": ma_chai}

    # 3. Tra DB
    bottle = crud.get_bottle_by_ma(db, ma_chai)

    # 3a. Không tồn tại trong DB
    if bottle is None:
        await device_manager.iobox.day_loai_chai()
        _log(db, None, ma_chai, "UNKNOWN", session_id)
        crud.bump_session(db, session_id, ok=False)
        return {"ket_qua": "UNKNOWN", "ma_chai": ma_chai}

    # 3b. Lấy giới hạn tái sử dụng từ lô NCC
    sup = db.get(models.SupplierBatch, bottle.supplier_batch_id)
    gioi_han = sup.so_lan_tai_su_dung if sup else 5

    # 3c. Đã bị loại trước đó (trạng thái âm) → loại tiếp
    if bottle.trang_thai is not None and bottle.trang_thai < 0:
        await device_manager.iobox.day_loai_chai()
        _log(db, bottle.id, ma_chai, "REJECTED", session_id)
        crud.bump_session(db, session_id, ok=False)
        return {
            "ket_qua": "REJECTED", "ma_chai": ma_chai,
            "so_lan_thuc_te": bottle.so_lan_thuc_te, "gioi_han": gioi_han,
        }

    # 3d. Vượt giới hạn → loại
    if bottle.so_lan_thuc_te >= gioi_han:
        await device_manager.iobox.day_loai_chai()
        _log(db, bottle.id, ma_chai, "OVER_LIMIT", session_id)
        crud.bump_session(db, session_id, ok=False)
        return {
            "ket_qua": "OVER_LIMIT", "ma_chai": ma_chai,
            "so_lan_thuc_te": bottle.so_lan_thuc_te, "gioi_han": gioi_han,
        }

    # 3e. OK → tăng đếm, cho qua
    crud.increment_reuse(db, bottle)
    _log(db, bottle.id, ma_chai, "OK", session_id)
    crud.bump_session(db, session_id, ok=True)
    return {
        "ket_qua": "OK", "ma_chai": ma_chai,
        "so_lan_thuc_te": bottle.so_lan_thuc_te, "gioi_han": gioi_han,
    }


def _log(db, bottle_id, ma, ket_qua, session_id):
    crud.log_event(db, bottle_id=bottle_id, ma_chai=ma,
                   event_type="SCAN", ket_qua=ket_qua, session_id=session_id)
