"""Kết nối DB. SQLite (dev) hoặc PostgreSQL (prod) — chỉ khác DATABASE_URL."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    """Dependency cho FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
