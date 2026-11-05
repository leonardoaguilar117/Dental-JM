"""Conexión a base de datos. SQLite por defecto; PostgreSQL si se define DATABASE_URL (Render)."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        os.makedirs("data", exist_ok=True)
        return "sqlite:///./data/crm_dental.db"
    # Render entrega URLs "postgres://", SQLAlchemy necesita "postgresql://"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


DATABASE_URL = _database_url()

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
