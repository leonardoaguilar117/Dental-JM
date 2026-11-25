"""Punto de entrada FastAPI · Consultorio Dental JM (demo ilustrativo)."""
import logging
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from . import config
from .database import Base, SessionLocal, engine
from .routers import appointments, auth, dashboard, finance, inventory, patients, reminders, settings
from .web import BASE_DIR, Forbidden, NotAuthenticated, redirect, templates

logging.basicConfig(level=logging.INFO)

if config.IS_PRODUCTION and config.SECRET_KEY == config.DEFAULT_SECRET:
    # Nunca la clave de ejemplo en producción. Si no se configuró SECRET_KEY, se usa una aleatoria por arranque:
    # es segura, pero las sesiones se cierran en cada reinicio. Defínela en Render > Environment para fijarla.
    import secrets
    config.SECRET_KEY = secrets.token_urlsafe(48)
    logging.getLogger("consultorio").warning(
        "SECRET_KEY no está definida: se generó una clave temporal. Agrégala en Render > Environment "
        "para que las sesiones no se cierren en cada reinicio.")

# Producción: sin documentación pública de la API (expone todas las rutas del expediente)
app = FastAPI(title=config.APP_NAME, version="1.0.0-demo", redoc_url=None,
              docs_url=None if config.IS_PRODUCTION else "/api/docs",
              openapi_url=None if config.IS_PRODUCTION else "/openapi.json")
app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY, session_cookie="jm_session",
                   max_age=60 * 60 * 8, same_site="lax", https_only=config.HTTPS_ONLY)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@app.middleware("http")
async def security_layer(request: Request, call_next):
    """Anti-CSRF (el origen de todo POST debe ser este mismo sitio) y cabeceras de seguridad."""
    if request.method not in SAFE_METHODS:
        source = request.headers.get("origin") or request.headers.get("referer") or ""
        if source and urlsplit(source).netloc != request.headers.get("host", ""):
            return PlainTextResponse("Solicitud rechazada: origen no permitido.", status_code=403)
    response = await call_next(request)
    h = response.headers
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"] = "DENY"
    h["Referrer-Policy"] = "same-origin"
    h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    h["Content-Security-Policy"] = "frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'"
    if config.HTTPS_ONLY:
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if not request.url.path.startswith("/static"):
        h["Cache-Control"] = "no-store"  # datos clínicos: que no queden en caché del navegador
    return response


for r in (auth, dashboard, patients, appointments, finance, reminders, inventory, settings):
    app.include_router(r.router)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_columns()
    _migrate_palette()
    if config.SEED_DEMO:
        from .seed import seed_if_empty

        with SessionLocal() as db:
            seed_if_empty(db)


# columnas agregadas después de la primera versión: (tabla, columna, DDL)
NEW_COLUMNS = [
    ("medical_histories", "consentimiento_firma", "TEXT DEFAULT ''"),
    ("medical_histories", "consentimiento_nombre", "VARCHAR(160) DEFAULT ''"),
    ("medical_histories", "consentimiento_fecha", "TIMESTAMP"),
    ("medical_histories", "lengua_hallazgos", "TEXT DEFAULT '[]'"),
    ("medical_histories", "lengua_notas", "TEXT DEFAULT ''"),
    ("medical_histories", "encia_hallazgos", "TEXT DEFAULT '[]'"),
    ("medical_histories", "encia_notas", "TEXT DEFAULT ''"),
    ("movements", "ticket", "VARCHAR(24) DEFAULT ''"),
    ("movements", "method", "VARCHAR(30) DEFAULT ''"),
    ("movements", "customer", "VARCHAR(120) DEFAULT ''"),
    ("users", "photo", "TEXT DEFAULT ''"),
    ("users", "cedula", "VARCHAR(20) DEFAULT ''"),
    ("users", "cedula_especialidad", "VARCHAR(20) DEFAULT ''"),
    ("users", "universidad", "VARCHAR(120) DEFAULT ''"),
    ("patients", "curp", "VARCHAR(18) DEFAULT ''"),
    ("patients", "estado_civil", "VARCHAR(20) DEFAULT ''"),
    ("patients", "lugar_nacimiento", "VARCHAR(80) DEFAULT ''"),
    ("medical_histories", "grupo_sanguineo", "VARCHAR(14) DEFAULT ''"),
    ("medical_histories", "aparatos_json", "TEXT DEFAULT '{}'"),
    ("medical_histories", "habitus_exterior", "TEXT DEFAULT ''"),
    ("medical_histories", "frecuencia_cardiaca", "VARCHAR(12) DEFAULT ''"),
    ("medical_histories", "frecuencia_respiratoria", "VARCHAR(12) DEFAULT ''"),
    ("medical_histories", "temperatura", "VARCHAR(12) DEFAULT ''"),
    ("medical_histories", "peso", "VARCHAR(12) DEFAULT ''"),
    ("medical_histories", "talla", "VARCHAR(12) DEFAULT ''"),
    ("medical_histories", "exploracion_atm", "TEXT DEFAULT ''"),
    ("medical_histories", "indice_placa", "VARCHAR(60) DEFAULT ''"),
    ("medical_histories", "estudios_complementarios", "TEXT DEFAULT ''"),
    ("medical_histories", "consentimiento_acto", "TEXT DEFAULT ''"),
    ("medical_histories", "consentimiento_riesgos", "TEXT DEFAULT ''"),
    ("medical_histories", "consentimiento_calidad", "VARCHAR(30) DEFAULT 'Paciente'"),
    ("medical_histories", "consentimiento_testigo1", "VARCHAR(160) DEFAULT ''"),
    ("medical_histories", "consentimiento_testigo2", "VARCHAR(160) DEFAULT ''"),
    ("medical_histories", "aviso_privacidad_fecha", "TIMESTAMP"),
    ("clinical_notes", "kind", "VARCHAR(30) DEFAULT 'Evolución'"),
    ("clinical_notes", "vitals", "VARCHAR(160) DEFAULT ''"),
    ("clinical_notes", "diagnosis", "VARCHAR(255) DEFAULT ''"),
    ("clinical_notes", "studies", "TEXT DEFAULT ''"),
    ("clinical_notes", "indications", "TEXT DEFAULT ''"),
    ("clinical_notes", "created_at", "TIMESTAMP"),
]


def _migrate_columns() -> None:
    """create_all no altera tablas existentes: agrega aquí las columnas que falten."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    with engine.begin() as conn:
        for table, column, ddl in NEW_COLUMNS:
            if column not in {c["name"] for c in insp.get_columns(table)}:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def _migrate_palette() -> None:
    """Bases creadas con la paleta anterior adoptan los colores nuevos (solo si no se personalizaron)."""
    from sqlalchemy import update

    from .models import ExternalSpecialist, User

    swaps = {"#0d9488": "#418d96", "#2563eb": "#6c4813"}
    with SessionLocal() as db:
        for old, new in swaps.items():
            db.execute(update(User).where(User.color == old).values(color=new))
        db.execute(update(ExternalSpecialist).where(ExternalSpecialist.color == "#7c3aed").values(color="#737a90"))
        db.commit()


@app.exception_handler(NotAuthenticated)
async def _not_auth(request: Request, exc: NotAuthenticated):
    return redirect("/login")


@app.exception_handler(Forbidden)
async def _forbidden(request: Request, exc: Forbidden):
    return templates.TemplateResponse(request, "error.html", {
        "code": 403, "title": "Módulo exclusivo",
        "message": "El inventario del depósito dental solo está disponible para la Dra. Jimena Juárez.",
        "user": None, "flashes": [], "notif_count": 0, "path": request.url.path}, status_code=403)


@app.exception_handler(StarletteHTTPException)
async def _http_error(request: Request, exc: StarletteHTTPException):
    if request.url.path.startswith("/api/"):
        from fastapi.responses import JSONResponse

        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return templates.TemplateResponse(request, "error.html", {
        "code": exc.status_code, "title": "No encontrado" if exc.status_code == 404 else "Error",
        "message": "La página o el registro que buscas no existe." if exc.status_code == 404 else str(exc.detail),
        "user": None, "flashes": [], "notif_count": 0, "path": request.url.path}, status_code=exc.status_code)


@app.get("/healthz", include_in_schema=False)
def health():
    return {"status": "ok"}
