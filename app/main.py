"""SATORI v2 — FastAPI app. Khởi động thiết bị + phục vụ UI + WebSocket."""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

# Console Windows mặc định cp1252 — ép UTF-8 để log tiếng Việt không crash.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from app.database import crud
from app.database.connection import SessionLocal
from app.devices.manager import device_manager
from app.paths import STATIC_DIR
from app.routers import batches, classify, identify, pages, reports, sessions
from app.services.classify import classify_bottle
from app.services.identify import identify_new_bottle
from app.ws import ws_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("satori")


# Tuần tự hóa xử lý quét: nhiều scanner chạy chung 1 event loop nên Lock này
# đảm bảo đọc-ghi DB nguyên tử (không lost-update counter tái sử dụng, tránh
# SQLite "database is locked") và chỉ 1 lệnh đẩy loại chạy mỗi lần.
_scan_lock = asyncio.Lock()


async def on_scan(ma_chai: str):
    """Callback chung cho mọi scanner. Xử lý PHÂN LOẠI và tự động ĐỊNH DANH."""
    async with _scan_lock:
        db = SessionLocal()
        try:
            # Chế độ PHÂN LOẠI
            sess = crud.get_active_session(db, "PHAN_LOAI")
            if sess:
                result = await classify_bottle(db, ma_chai, sess.id)
                # Quét trùng VẪN broadcast để UI BÁO ĐỎ cho công nhân thấy,
                # nhưng frontend sẽ không đếm/không thêm dòng (xem classify.js).
                iobox_fault = result.pop("iobox_fault", False)
                result["event"] = "scan"
                result["tong_hop_le"] = sess.tong_hop_le
                result["tong_loi"] = sess.tong_loi
                if iobox_fault:
                    await ws_manager.broadcast({
                        "event": "iobox_fault", "ma_chai": ma_chai,
                        "message": "IO-Box lỗi — chai có thể không bị đẩy ra! "
                                   "Dừng băng tải và kiểm tra ngay.",
                    })
                await ws_manager.broadcast(result)
                return

            # Chế độ ĐỊNH DANH — scanner kích hoạt tự động in mã
            sess = crud.get_active_session(db, "DINH_DANH")
            if sess:
                result = await identify_new_bottle(db, sess.production_batch_id, sess.id)
                if result.get("ket_qua") == "PRINT_FAILED":
                    await ws_manager.broadcast({
                        "event": "print_failed",
                        "ma_chai": result.get("ma_chai"),
                        "message": result.get("message"),
                    })
                else:
                    result["event"] = "print"
                    await ws_manager.broadcast(result)
                return

            log.info("Quét '%s' — không có ca đang chạy, bỏ qua.", ma_chai)
        except Exception:
            # Lỗi thiết bị (IO-Box/Laser mất kết nối...) KHÔNG được làm sập
            # vòng lắng nghe scanner. Ghi log + báo UI, rồi tiếp tục chai sau.
            log.exception("Lỗi xử lý quét '%s'", ma_chai)
            try:
                await ws_manager.broadcast({
                    "event": "error", "ma_chai": ma_chai,
                    "message": "Lỗi xử lý — kiểm tra thiết bị/log",
                })
            except Exception:
                pass
        finally:
            db.close()


async def _heartbeat():
    """Ping định kỳ qua WS để client phát hiện kết nối chết (half-open)."""
    while True:
        await asyncio.sleep(10)
        try:
            await ws_manager.broadcast({"event": "heartbeat"})
        except Exception:
            pass


async def _device_monitor():
    """Theo dõi trạng thái thiết bị, broadcast ngay khi có thiết bị mất kết nối."""
    prev: dict[str, str] = {}
    while True:
        await asyncio.sleep(3)
        try:
            status = await device_manager.status()
            for key in ("scanner", "iobox", "laser"):
                cur = status.get(key, "OFFLINE")
                if prev.get(key) == "OK" and cur != "OK":
                    await ws_manager.broadcast({
                        "event": "device_change",
                        "device": key,
                        "status": "OFFLINE",
                    })
                prev[key] = cur
        except Exception:
            pass


def _recover_stuck_sessions():
    """Đóng session bị treo từ lần khởi động trước (mất điện / crash)."""
    db = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(hours=16)
        stuck = (db.query(crud.models.Session)
                 .filter(crud.models.Session.ket_thuc.is_(None),
                         crud.models.Session.bat_dau < cutoff)
                 .all())
        for s in stuck:
            s.ket_thuc = datetime.now()
            log.warning("Tự đóng session treo: id=%s bat_dau=%s", s.id, s.bat_dau)
        if stuck:
            db.commit()
    except Exception:
        log.exception("Lỗi khi phục hồi session treo")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.config import settings
    _recover_stuck_sessions()
    device_manager.setup(on_scan)
    await device_manager.connect_all()
    await device_manager.start_scanners()
    tasks = [
        asyncio.create_task(_heartbeat()),
        asyncio.create_task(_device_monitor()),
    ]
    if settings.backup_enabled:
        from app.services.backup import backup_loop
        tasks.append(asyncio.create_task(backup_loop()))
    log.info("SATORI v2 đã khởi động.")
    yield
    for t in tasks:
        t.cancel()
    await device_manager.stop_scanners()


app = FastAPI(title="SATORI v2", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(pages.router)
app.include_router(sessions.router, prefix="/api")
app.include_router(classify.router, prefix="/api")
app.include_router(identify.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(batches.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/is-mock")
def is_mock():
    from app.config import settings
    return {"mock": settings.use_mock_devices}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
