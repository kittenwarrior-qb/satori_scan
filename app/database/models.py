"""Bảng dữ liệu (SQLAlchemy) — theo docs/02_DATA_MODEL.md."""
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, ForeignKey, func
)
from sqlalchemy.orm import relationship

from app.database.connection import Base


# ── Mã trạng thái chai khi BỊ LOẠI (trang_thai < 0) ──────────────────────────
# trang_thai >= 0 : số lần đã tái sử dụng (0 = chai mới).
# trang_thai <  0 : đã loại — giá trị âm cho biết LÝ DO (giống cách CodeIT
#                   dùng trạng thái âm). Có chú thích trên màn Báo cáo cho NV.
REJECT_OVER_LIMIT = -1   # loại tự động: quá số lần tái sử dụng cho phép
REJECT_BAD_CODE   = -2   # loại tự động: mã không đọc được / không hợp lệ
REJECT_MANUAL     = -3   # loại thủ công: không đạt cảm quan (trầy, móp, nứt)

REJECT_REASONS = {
    REJECT_OVER_LIMIT: "Quá hạn tái sử dụng",
    REJECT_BAD_CODE:   "Mã lỗi/không đọc được",
    REJECT_MANUAL:     "Không đạt cảm quan",
}


class SupplierBatch(Base):
    """Lô nhà cung cấp (mặc định Ngọc Nghĩa)."""
    __tablename__ = "supplier_batches"
    id = Column(Integer, primary_key=True)
    nha_cung_cap = Column(String, default="Ngọc Nghĩa")
    so_lo_ncc = Column(String, unique=True, nullable=False)
    so_luong_chai = Column(Integer, default=0)
    so_lan_tai_su_dung = Column(Integer, default=5)  # giới hạn TSD
    created_at = Column(DateTime, server_default=func.now())


class ProductionBatch(Base):
    """Lô sản xuất (do Satori quản lý)."""
    __tablename__ = "production_batches"
    id = Column(Integer, primary_key=True)
    supplier_batch_id = Column(Integer, ForeignKey("supplier_batches.id"))
    so_lo_san_xuat = Column(String, unique=True, nullable=False)
    ngay_san_xuat = Column(Date, nullable=False)
    counter = Column(Integer, default=0)  # bộ đếm in mã
    created_at = Column(DateTime, server_default=func.now())

    supplier_batch = relationship("SupplierBatch")


class Bottle(Base):
    """Chai — định danh bằng ma_chai duy nhất."""
    __tablename__ = "bottles"
    id = Column(Integer, primary_key=True)
    ma_chai = Column(String, unique=True, nullable=False, index=True)
    production_batch_id = Column(
        Integer, ForeignKey("production_batches.id"), index=True)
    supplier_batch_id = Column(
        Integer, ForeignKey("supplier_batches.id"), index=True)
    so_lan_thuc_te = Column(Integer, default=0)
    trang_thai = Column(Integer, default=0)   # 0=mới, N=đã dùng N lần, âm=loại
    ngay_san_xuat = Column(Date)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    production_batch = relationship("ProductionBatch")
    supplier_batch = relationship("SupplierBatch")


class Session(Base):
    """Ca/phiên sản xuất."""
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    che_do = Column(String, nullable=False)   # DINH_DANH/PHAN_LOAI/LOAI_BO
    production_batch_id = Column(Integer, ForeignKey("production_batches.id"))
    bat_dau = Column(DateTime, server_default=func.now(), index=True)
    ket_thuc = Column(DateTime)
    tong_hop_le = Column(Integer, default=0)
    tong_loi = Column(Integer, default=0)
    operator = Column(String)

    production_batch = relationship("ProductionBatch")


class ScanEvent(Base):
    """Lịch sử quét/in/loại — audit log."""
    __tablename__ = "scan_events"
    id = Column(Integer, primary_key=True)
    bottle_id = Column(Integer, ForeignKey("bottles.id"), nullable=True)
    ma_chai = Column(String, index=True)
    event_type = Column(String)   # PRINT/SCAN/REJECT
    ket_qua = Column(String)      # OK/NOREAD/OVER_LIMIT/UNKNOWN/REJECTED
    session_id = Column(Integer, ForeignKey("sessions.id"), index=True)
    scanned_at = Column(DateTime, server_default=func.now(), index=True)
