"""API cho chức năng PHÂN LOẠI + LOẠI BỎ."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import crud, models
from app.database.connection import get_db
from app.devices.manager import device_manager
from app.services.reject import reject_bottle

router = APIRouter()


@router.get("/classify/scans")
def classify_scans(limit: int = 200, db: Session = Depends(get_db)):
    """Nạp lại danh sách quét của ca PHÂN LOẠI đang chạy để khôi phục màn hình
    sau khi chuyển tab. Trả mới → cũ; kèm tổng để khôi phục bộ đếm."""
    sess = crud.get_active_session(db, "PHAN_LOAI")
    if not sess:
        return {"active": False, "scans": [],
                "tong_hop_le": 0, "tong_loi": 0, "count": 0}

    scans = []
    for e in crud.list_scan_events_for_session(db, sess.id, limit):
        gioi_han = so_lan = None
        if e.bottle_id:
            b = db.get(models.Bottle, e.bottle_id)
            if b:
                so_lan = b.so_lan_thuc_te
                sup = db.get(models.SupplierBatch, b.supplier_batch_id)
                gioi_han = sup.so_lan_tai_su_dung if sup else None
        scans.append({
            "ma_chai": e.ma_chai,
            "ket_qua": e.ket_qua,
            "scanned_at": e.scanned_at.isoformat() if e.scanned_at else None,
            "gioi_han": gioi_han,
            "so_lan_thuc_te": so_lan,
        })

    return {
        "active": True,
        "scans": scans,
        "tong_hop_le": sess.tong_hop_le,
        "tong_loi": sess.tong_loi,
        "count": sess.tong_hop_le + sess.tong_loi,
    }


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
