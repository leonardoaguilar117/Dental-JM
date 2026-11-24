"""Helpers compartidos por los routers: sesión, plantillas, mensajes flash."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import config
from .database import get_db
from .models import User
from .services import notifications
from .utils import fecha, money, money0, relative_days, today_local, whatsapp_link

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["money"] = money
templates.env.filters["money0"] = money0
templates.env.filters["fecha"] = fecha
templates.env.filters["rel"] = relative_days
templates.env.filters["qty"] = lambda v: f"{float(v or 0):,.2f}".rstrip("0").rstrip(".")
templates.env.globals["wa"] = whatsapp_link
templates.env.globals["cfg"] = config
templates.env.globals["today"] = today_local


class NotAuthenticated(Exception):
    pass


class Forbidden(Exception):
    pass


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    uid = request.session.get("uid")
    user = db.get(User, uid) if uid else None
    if not user:
        raise NotAuthenticated()
    return user


def inventory_user(user: User = Depends(current_user)) -> User:
    if not user.can_inventory:
        raise Forbidden()
    return user


def flash(request: Request, message: str, kind: str = "ok") -> None:
    request.session.setdefault("_flash", []).append({"m": message, "k": kind})


def pop_flash(request: Request) -> list[dict]:
    return request.session.pop("_flash", [])


THEMES = {
    "lavanda": {"name": "Lavanda", "swatches": ["#c0cde6", "#012880", "#a393be"], "desc": "Claro · azul marino y lavanda"},
    "noche": {"name": "Lavanda noche", "swatches": ["#161a2e", "#b8b0dc", "#c0cde6"], "desc": "Oscuro · la misma paleta, para poca luz"},
}
# temas retirados: quien los tenía guardados cae al equivalente claro u oscuro
LEGACY_THEMES = {"arrecife": "noche", "grafito": "lavanda"}
DEFAULT_THEME = "lavanda"
templates.env.globals["THEMES"] = THEMES


def _nav_counts(db: Session, user: User) -> dict:
    """Viñetas del menú: lo que espera en cada sección."""
    from datetime import datetime, timedelta

    from sqlalchemy import func, select

    from .models import Appointment, Patient, Reminder
    from .services import inventory

    t0 = datetime.combine(today_local(), datetime.min.time())
    out = {
        "agenda": db.scalar(select(func.count(Appointment.id)).where(
            Appointment.doctor_id == user.id, Appointment.start >= t0, Appointment.start < t0 + timedelta(days=1),
            Appointment.status.in_(["programada", "confirmada"]))) or 0,
        "pacientes": db.scalar(select(func.count(Patient.id)).where(Patient.active)) or 0,
        "recordatorios": db.scalar(select(func.count(Reminder.id)).where(
            Reminder.doctor_id == user.id, Reminder.status == "pendiente",
            Reminder.due_date <= today_local() + timedelta(days=7))) or 0,
    }
    if user.can_inventory:
        a = inventory.alerts(db, user.id)
        out["inventario"] = len(a["expired"]) + len(a["expiring"]) + len(a["low"])
        out["inventario_urgente"] = bool(a["expired"])
    return out


def render(request: Request, template: str, db: Session, user: User | None, **ctx):
    theme = request.cookies.get("jm_theme", DEFAULT_THEME)
    ctx.update(
        user=user,
        flashes=pop_flash(request),
        notif_count=notifications.count_only(db, user) if user else 0,
        nav=_nav_counts(db, user) if user else {},
        theme=theme if theme in THEMES else LEGACY_THEMES.get(theme, DEFAULT_THEME),
        path=request.url.path,
    )
    return templates.TemplateResponse(request, template, ctx)


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)
