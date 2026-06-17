"""API quản lý ca/phiên sản xuất + trạng thái thiết bị."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import crud
from app.database.connection import get_db
from app.devices.manager import device_manager

router = APIRouter()

VALID_MODES = {"DINH_DANH", "PHAN_LOAI", "LOAI_BO"}


@router.post("/sessions/start")
async def start(che_do: str, production_batch_id: int,
                operator: str = "operator", db: Session = Depends(get_db)):
    if che_do not in VALID_MODES:
        raise HTTPException(400, f"che_do không hợp lệ: {che_do}")
    if crud.get_active_session(db, che_do):
        raise HTTPException(400, "Đã có ca đang chạy")
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
    # Tắt băng tải khi kết thúc ca PHÂN LOẠI
    if che_do == "PHAN_LOAI":
        await device_manager.iobox.stop_bang_tai()
    return {"message": "Đã kết thúc", "id": s.id,
            "tong_hop_le": s.tong_hop_le, "tong_loi": s.tong_loi}


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
