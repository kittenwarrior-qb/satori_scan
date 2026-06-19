"""Logic PHÂN LOẠI chai — trái tim hệ thống. Quyết định OK hay loại."""
import logging
import time

from sqlalchemy.orm import Session

from app.config import settings
from app.database import crud, models
from app.devices.manager import device_manager
from app.services.ma_chai import parse_ma_chai

log = logging.getLogger("satori.classify")

# Thời điểm quét gần nhất theo từng mã (chống quét trùng). Vì on_scan chạy dưới
# 1 asyncio.Lock chung nên truy cập dict này không có tranh chấp.
_last_seen: dict[str, float] = {}


def reset_debounce() -> None:
    """Xóa bộ nhớ chống quét trùng — gọi khi bắt đầu ca mới."""
    _last_seen.clear()


def _seen_recently(ma_chai: str, window: float) -> bool:
    """True nếu mã vừa được quét trong vòng `window` giây (= quét trùng)."""
    now = time.monotonic()
    last = _last_seen.get(ma_chai)
    _last_seen[ma_chai] = now
    if len(_last_seen) > 10000:                      # dọn bộ nhớ định kỳ
        cutoff = now - max(window, 1.0)
        for k in [k for k, t in _last_seen.items() if t < cutoff]:
            del _last_seen[k]
    return last is not None and (now - last) < window


async def _eject(label: str) -> bool:
    """Đẩy loại chai qua IO-Box. Trả True nếu thành công, False nếu IO-Box lỗi."""
    try:
        await device_manager.iobox.day_loai_chai()
        return True
    except Exception as exc:
        log.error("IO-Box lỗi khi đẩy '%s': %s", label, exc)
        return False


async def classify_bottle(db: Session, ma_chai: str, session_id: int) -> dict:
    """Xử lý 1 lần quét. Tự gọi đẩy loại nếu cần. Trả về kết quả."""
    # 1. NoRead (scanner báo không đọc được / chuỗi rỗng)
    if not ma_chai or ma_chai == "NOREAD":
        ejected = await _eject("NOREAD")
        _log(db, None, ma_chai or "", "NOREAD", session_id)
        crud.bump_session(db, session_id, ok=False)
        return {"ket_qua": "NOREAD", "ma_chai": None, "iobox_fault": not ejected}

    # 2. Format sai → coi như không đọc được
    if parse_ma_chai(ma_chai) is None:
        ejected = await _eject("FORMAT_ERR")
        _log(db, None, ma_chai, "NOREAD", session_id)
        crud.bump_session(db, session_id, ok=False)
        return {"ket_qua": "NOREAD", "ma_chai": ma_chai, "iobox_fault": not ejected}

    # 2b. Chống quét trùng — cùng 1 chai bị kích quét 2 lần liên tiếp (nhiễu băng
    #     tải / cảm biến / quét tay lặp). KHÔNG đẩy loại, KHÔNG tăng đếm tái sử
    #     dụng, KHÔNG cộng thống kê → tránh đếm sai số chai và tăng nhầm TSD.
    if settings.classify_debounce_sec > 0 and \
            _seen_recently(ma_chai, settings.classify_debounce_sec):
        log.info("Quét trùng '%s' trong %.1fs — bỏ qua.",
                 ma_chai, settings.classify_debounce_sec)
        return {"ket_qua": "DUPLICATE", "ma_chai": ma_chai}

    # 3. Tra DB
    bottle = crud.get_bottle_by_ma(db, ma_chai)

    # 3a. Không tồn tại trong DB
    if bottle is None:
        ejected = await _eject("UNKNOWN")
        _log(db, None, ma_chai, "UNKNOWN", session_id)
        crud.bump_session(db, session_id, ok=False)
        return {"ket_qua": "UNKNOWN", "ma_chai": ma_chai, "iobox_fault": not ejected}

    # 3b. Lấy giới hạn tái sử dụng từ lô NCC
    sup = db.get(models.SupplierBatch, bottle.supplier_batch_id)
    gioi_han = sup.so_lan_tai_su_dung if sup else 5

    # 3c. Đã bị loại trước đó (trạng thái âm) → loại tiếp
    if bottle.trang_thai is not None and bottle.trang_thai < 0:
        ejected = await _eject("REJECTED")
        _log(db, bottle.id, ma_chai, "REJECTED", session_id)
        crud.bump_session(db, session_id, ok=False)
        return {
            "ket_qua": "REJECTED", "ma_chai": ma_chai,
            "so_lan_thuc_te": bottle.so_lan_thuc_te, "gioi_han": gioi_han,
            "iobox_fault": not ejected,
        }

    # 3d. Vượt giới hạn → loại + đánh dấu trạng thái âm (lý do: quá hạn TSD)
    if bottle.so_lan_thuc_te >= gioi_han:
        ejected = await _eject("OVER_LIMIT")
        bottle.trang_thai = models.REJECT_OVER_LIMIT
        db.commit()
        _log(db, bottle.id, ma_chai, "OVER_LIMIT", session_id)
        crud.bump_session(db, session_id, ok=False)
        return {
            "ket_qua": "OVER_LIMIT", "ma_chai": ma_chai,
            "so_lan_thuc_te": bottle.so_lan_thuc_te, "gioi_han": gioi_han,
            "iobox_fault": not ejected,
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
