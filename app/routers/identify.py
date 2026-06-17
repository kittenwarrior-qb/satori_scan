"""API cho chức năng ĐỊNH DANH chai mới."""
import qrcode
import io
import base64

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import crud
from app.database.connection import get_db
from app.services.identify import identify_new_bottle
from app.ws import ws_manager

router = APIRouter()


@router.get("/identify/batches")
def list_batches(db: Session = Depends(get_db)):
    """Danh sách lô SX để chọn khi định danh."""
    out = []
    for b in crud.list_production_batches(db):
        sup = b.supplier_batch
        out.append({
            "id": b.id,
            "so_lo_san_xuat": b.so_lo_san_xuat,
            "ngay_san_xuat": b.ngay_san_xuat.strftime("%d/%m/%Y")
            if b.ngay_san_xuat else "",
            "counter": b.counter,
            "nha_cung_cap": sup.nha_cung_cap if sup else "",
            "so_lo_ncc": sup.so_lo_ncc if sup else "",
            "so_luong_chai": sup.so_luong_chai if sup else 0,
            "so_lan_tai_su_dung": sup.so_lan_tai_su_dung if sup else 0,
        })
    return out


@router.post("/identify/print")
async def print_one(production_batch_id: int, db: Session = Depends(get_db)):
    """In mã cho 1 chai mới. Broadcast kết quả qua WebSocket."""
    sess = crud.get_active_session(db, "DINH_DANH")
    if not sess:
        raise HTTPException(400, "Chưa bắt đầu ca định danh")
    result = await identify_new_bottle(db, production_batch_id, sess.id)
    if result.get("ket_qua") != "OK":
        raise HTTPException(400, result.get("message", "Lỗi định danh"))
    result["event"] = "print"
    await ws_manager.broadcast(result)
    return result


@router.get("/qr")
def qr_code(data: str):
    """Sinh QR code base64 (PNG) cho mã chai — hiển thị trên UI."""
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return {"data": data, "png_base64": f"data:image/png;base64,{b64}"}
