"""SATORI v2 — FastAPI app. Khởi động thiết bị + phục vụ UI + WebSocket."""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

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


async def on_scan(ma_chai: str):
    """Callback chung cho mọi scanner. Xử lý PHÂN LOẠI và tự động ĐỊNH DANH."""
    db = SessionLocal()
    try:
        # Chế độ PHÂN LOẠI
        sess = crud.get_active_session(db, "PHAN_LOAI")
        if sess:
            result = await classify_bottle(db, ma_chai, sess.id)
            result["event"] = "scan"
            result["tong_hop_le"] = sess.tong_hop_le
            result["tong_loi"] = sess.tong_loi
            await ws_manager.broadcast(result)
            return

        # Chế độ ĐỊNH DANH — scanner kích hoạt tự động in mã
        sess = crud.get_active_session(db, "DINH_DANH")
        if sess:
            result = await identify_new_bottle(db, sess.production_batch_id, sess.id)
            result["event"] = "print"
            await ws_manager.broadcast(result)
            return

        log.info("Quét '%s' — không có ca đang chạy, bỏ qua.", ma_chai)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    device_manager.setup(on_scan)
    await device_manager.connect_all()
    await device_manager.start_scanners()
    log.info("SATORI v2 đã khởi động.")
    yield
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
