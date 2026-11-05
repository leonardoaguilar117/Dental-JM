"""Punto de entrada FastAPI · Consultorio Dental JM (demo ilustrativo)."""
import logging

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from . import config
from .database import Base, SessionLocal, engine
from .routers import appointments, auth, dashboard, finance, inventory, patients, reminders, settings
from .web import BASE_DIR, Forbidden, NotAuthenticated, redirect, templates

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=config.APP_NAME, version="1.0.0-demo", docs_url="/api/docs", redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY, session_cookie="jm_session",
                   max_age=60 * 60 * 12, same_site="lax", https_only=False)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

for r in (auth, dashboard, patients, appointments, finance, reminders, inventory, settings):
    app.include_router(r.router)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_palette()
    if config.SEED_DEMO:
        from .seed import seed_if_empty

        with SessionLocal() as db:
            seed_if_empty(db)


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
