"""API cho chức năng PHÂN LOẠI + LOẠI BỎ."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import crud
from app.database.connection import get_db
from app.devices.manager import device_manager
from app.services.reject import reject_bottle

router = APIRouter()


@router.post("/classify/test")
async def classify_test(ma_chai: str):
    """Giả lập 1 lần quét (dev/mock). Đi qua đúng pipeline scanner → on_scan → WS."""
    scanner = device_manager.scanner
    if scanner is None or not hasattr(scanner, "inject_scan"):
        raise HTTPException(400, "Chỉ hoạt động khi USE_MOCK_DEVICES=true")
    await scanner.inject_scan(ma_chai)
    return {"injected": ma_chai}


@router.post("/identify/test")
async def identify_test():
    """Giả lập scanner kích hoạt 1 lần trong chế độ ĐỊNH DANH (mock)."""
    scanner = device_manager.scanner
    if scanner is None or not hasattr(scanner, "inject_scan"):
        raise HTTPException(400, "Chỉ hoạt động khi USE_MOCK_DEVICES=true")
    # Gửi bất kỳ giá trị — on_scan() sẽ tự nhận diện chế độ ĐỊNH DANH
    await scanner.inject_scan("TRIGGER")
    return {"injected": "TRIGGER"}


@router.post("/reject")
def reject(ma_chai: str, db: Session = Depends(get_db)):
    """Loại bỏ chai thủ công (màn hình Loại bỏ)."""
    sess = crud.get_active_session(db, "LOAI_BO") or \
        crud.get_active_session(db, "PHAN_LOAI")
    session_id = sess.id if sess else None
    return reject_bottle(db, ma_chai.strip(), session_id)
