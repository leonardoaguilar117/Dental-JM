"""Conexión a base de datos.

- SQLite (por defecto): un archivo dentro del contenedor, en DATA_DIR (./data en local). En Render, DATA_DIR
  apunta al disco persistente montado en el servicio (/var/data) para que la base sobreviva despliegues.
- PostgreSQL: si se define DATABASE_URL.
"""
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATA_DIR = os.getenv("DATA_DIR", "").strip() or "data"


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        os.makedirs(DATA_DIR, exist_ok=True)
        return f"sqlite:///{os.path.join(DATA_DIR, 'crm_dental.db')}"
    # Render entrega URLs "postgres://", SQLAlchemy necesita "postgresql://"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


DATABASE_URL = _database_url()

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 15})

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        # WAL: lecturas sin bloquear escrituras y menos riesgo de corrupción si el contenedor se detiene a medias
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=15000")
        cur.close()
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
