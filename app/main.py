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

            # Không có ca nào đang chạy: KHÔNG xử lý/đếm/lưu, nhưng vẫn báo lên
            # màn hình để công nhân biết cần bấm "Bắt đầu" (tránh im lặng khó hiểu).
            log.info("Quét '%s' — không có ca đang chạy, bỏ qua.", ma_chai)
            await ws_manager.broadcast({
                "event": "scan_no_session", "ma_chai": ma_chai,
            })
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


def _ensure_db():
    """Tự tạo thư mục data + bảng DB nếu chưa có. An toàn chạy lại nhiều lần
    (KHÔNG xoá dữ liệu sẵn có — chỉ tạo bảng/index còn thiếu)."""
    import os as _os
    from app.database.connection import Base, engine
    from app.database import models  # noqa: F401 — đăng ký bảng vào metadata
    _os.makedirs("data", exist_ok=True)
    _os.makedirs("data/reports", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _indexes = [
        ("ix_bottles_ma_chai", "bottles", "ma_chai"),
        ("ix_bottles_ngay_san_xuat", "bottles", "ngay_san_xuat"),
        ("ix_bottles_production_batch_id", "bottles", "production_batch_id"),
        ("ix_bottles_supplier_batch_id", "bottles", "supplier_batch_id"),
        ("ix_scan_events_ma_chai", "scan_events", "ma_chai"),
        ("ix_scan_events_scanned_at", "scan_events", "scanned_at"),
        ("ix_sessions_bat_dau", "sessions", "bat_dau"),
    ]
    with engine.begin() as conn:
        for name, table, col in _indexes:
            conn.exec_driver_sql(
                f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({col})")
    log.info("DB sẵn sàng (bảng + index đã kiểm tra).")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.config import settings
    _ensure_db()
    device_manager.setup(on_scan)
    await device_manager.connect_all()
    await device_manager.start_scanners()
    backup_task = None
    if settings.backup_enabled:
        from app.services.backup import backup_loop
        backup_task = asyncio.create_task(backup_loop())
    log.info("SATORI v2 đã khởi động.")
    yield
    if backup_task:
        backup_task.cancel()
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
