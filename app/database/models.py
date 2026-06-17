"""Bảng dữ liệu (SQLAlchemy) — theo docs/02_DATA_MODEL.md."""
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, ForeignKey, func
)
from sqlalchemy.orm import relationship

from app.database.connection import Base


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
    production_batch_id = Column(Integer, ForeignKey("production_batches.id"))
    supplier_batch_id = Column(Integer, ForeignKey("supplier_batches.id"))
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
    bat_dau = Column(DateTime, server_default=func.now())
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
    ma_chai = Column(String)
    event_type = Column(String)   # PRINT/SCAN/REJECT
    ket_qua = Column(String)      # OK/NOREAD/OVER_LIMIT/UNKNOWN/REJECTED
    session_id = Column(Integer, ForeignKey("sessions.id"))
    scanned_at = Column(DateTime, server_default=func.now())
