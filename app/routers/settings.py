import secrets

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ExternalSpecialist, User
from ..services import gcal
from ..utils import hash_password, to_float, verify_password
from ..web import current_user, flash, redirect, render

router = APIRouter(prefix="/configuracion")


@router.get("")
def settings(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    base = str(request.base_url).rstrip("/")
    if request.headers.get("x-forwarded-proto") == "https":
        base = base.replace("http://", "https://", 1)
    ics_url = f"{base}/calendario/{user.ical_token}.ics"
    return render(request, "settings.html", db, user, ics_url=ics_url,
                  doctors=db.scalars(select(User).order_by(User.id)).all(),
                  externals=db.scalars(select(ExternalSpecialist)).all(),
                  gcal_api=gcal.api_enabled(), sa_email=gcal.service_account_email())


@router.post("/perfil")
async def profile(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = await request.form()
    user.phone = str(f.get("phone", "")).strip()
    user.color = str(f.get("color") or user.color)
    user.gcal_calendar_id = str(f.get("gcal_calendar_id", "")).strip()
    db.commit()
    flash(request, "Perfil actualizado.")
    return redirect("/configuracion")


@router.post("/reparto")
async def split(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = await request.form()
    doctors = db.scalars(select(User).order_by(User.id)).all()
    values = {d.id: to_float(f.get(f"pct_{d.id}")) for d in doctors}
    if abs(sum(values.values()) - 100) > 0.01:
        flash(request, "Los porcentajes deben sumar 100%.", "error")
        return redirect("/configuracion")
    for d in doctors:
        d.shared_expense_pct = values[d.id]
    db.commit()
    flash(request, "Reparto de gastos compartidos actualizado.")
    return redirect("/configuracion")


@router.post("/password")
async def password(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = await request.form()
    if not verify_password(str(f.get("current", "")), user.password_hash):
        flash(request, "La contraseña actual no es correcta.", "error")
    elif len(str(f.get("new", ""))) < 6:
        flash(request, "La nueva contraseña debe tener al menos 6 caracteres.", "error")
    else:
        user.password_hash = hash_password(str(f["new"]))
        db.commit()
        flash(request, "Contraseña actualizada.")
    return redirect("/configuracion")


@router.post("/ical/regenerar")
def regen_ical(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    user.ical_token = secrets.token_urlsafe(24)
    db.commit()
    flash(request, "Se generó un nuevo enlace iCal. Actualiza la suscripción en Google Calendar.")
    return redirect("/configuracion")


@router.post("/especialistas")
async def save_specialist(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = await request.form()
    sid = f.get("id")
    s = db.get(ExternalSpecialist, int(sid)) if sid else ExternalSpecialist()
    s.full_name = str(f.get("full_name", "")).strip()
    s.specialty = str(f.get("specialty", "")).strip() or "Cirujano maxilofacial"
    s.phone = str(f.get("phone", "")).strip()
    s.email = str(f.get("email", "")).strip()
    s.availability_note = str(f.get("availability_note", "")).strip()
    s.color = str(f.get("color") or "#7c3aed")
    s.active = f.get("active") == "on"
    if not s.full_name:
        flash(request, "El nombre del especialista es obligatorio.", "error")
        return redirect("/configuracion")
    db.add(s)
    db.commit()
    flash(request, f"Especialista {s.full_name} guardado.")
    return redirect("/configuracion#especialistas")
