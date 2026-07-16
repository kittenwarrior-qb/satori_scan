"""API quản lý ca/phiên sản xuất + trạng thái thiết bị."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import crud
from app.database.connection import get_db
from app.devices.manager import device_manager

log = logging.getLogger("satori.sessions")

router = APIRouter()

VALID_MODES = {"DINH_DANH", "PHAN_LOAI", "LOAI_BO"}

# ĐỊNH DANH và PHÂN LOẠI dùng chung băng chuyền/scanner vật lý — theo tài
# liệu gốc, chỉ 1 trong 2 được chạy tại một thời điểm ("Kết thúc chức năng
# kia nếu vẫn đang chạy" trước khi Bắt đầu). LOẠI BỎ dùng scanner cầm tay
# riêng nên không bị ràng buộc.
_EXCLUSIVE_MODE = {"DINH_DANH": "PHAN_LOAI", "PHAN_LOAI": "DINH_DANH"}
_MODE_LABEL = {"DINH_DANH": "Định danh", "PHAN_LOAI": "Phân loại"}


@router.post("/sessions/start")
async def start(che_do: str, production_batch_id: int,
                operator: str = "operator", db: Session = Depends(get_db)):
    if che_do not in VALID_MODES:
        raise HTTPException(400, f"che_do không hợp lệ: {che_do}")
    if crud.get_active_session(db, che_do):
        raise HTTPException(400, "Đã có ca đang chạy")
    other = _EXCLUSIVE_MODE.get(che_do)
    if other and crud.get_active_session(db, other):
        raise HTTPException(
            400, f"Đang có ca {_MODE_LABEL[other]} chạy — vui lòng bấm "
                 f"\"Kết thúc sản xuất\" ở màn {_MODE_LABEL[other]} trước "
                 f"khi {_MODE_LABEL[che_do]}")
    s = crud.start_session(db, che_do, production_batch_id, operator)
    # Bật băng tải khi bắt đầu ca PHÂN LOẠI
    if che_do == "PHAN_LOAI":
        try:
            await device_manager.iobox.start_bang_tai()
        except Exception as e:
            # Băng tải không bật được → đừng để ca "treo" trong DB.
            crud.end_session(db, s)
            raise HTTPException(503, f"Không bật được băng tải: {e}")
    return {"id": s.id, "che_do": s.che_do,
            "production_batch_id": s.production_batch_id}


@router.post("/sessions/end")
async def end(che_do: str, db: Session = Depends(get_db)):
    s = crud.get_active_session(db, che_do)
    if not s:
        raise HTTPException(400, "Không có ca đang chạy")
    crud.end_session(db, s)
    # Tắt băng tải khi kết thúc ca PHÂN LOẠI. Ca đã ĐƯỢC KẾT THÚC trong DB rồi
    # (dòng trên) — nếu PLC từ chối lệnh tắt băng tải thì KHÔNG được để lỗi đó
    # làm hỏng luôn request "kết thúc ca" (trước đây thiếu try/except ở đây:
    # PLC từ chối → 500 lỗi → operator thấy toast lỗi và tưởng ca CHƯA kết
    # thúc, trong khi DB đã ghi kết thúc rồi — sai lệch giữa DB và màn hình).
    bang_tai_warning = None
    if che_do == "PHAN_LOAI":
        try:
            await device_manager.iobox.stop_bang_tai()
        except Exception as e:
            log.error("Không tắt được băng tải khi kết thúc ca %s: %s", s.id, e)
            bang_tai_warning = f"Ca đã kết thúc nhưng KHÔNG tắt được băng tải tự động — tắt tay: {e}"
    resp = {"message": "Đã kết thúc", "id": s.id,
            "tong_hop_le": s.tong_hop_le, "tong_loi": s.tong_loi}
    if bang_tai_warning:
        resp["warning"] = bang_tai_warning
    return resp


@router.get("/sessions/active")
def active(che_do: Optional[str] = None, db: Session = Depends(get_db)):
    s = crud.get_active_session(db, che_do)
    if not s:
        return {"active": False}
    return {
        "active": True, "id": s.id, "che_do": s.che_do,
        "production_batch_id": s.production_batch_id,
        "tong_hop_le": s.tong_hop_le, "tong_loi": s.tong_loi,
    }


@router.get("/devices/status")
async def devices_status():
    return await device_manager.status()
