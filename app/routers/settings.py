from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..services import gcal
from ..utils import hash_password, to_float, verify_password
from ..web import current_user, flash, redirect, render

router = APIRouter(prefix="/configuracion")


@router.get("")
def settings(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return render(request, "settings.html", db, user,
                  doctors=db.scalars(select(User).order_by(User.id)).all(),
                  gcal_api=gcal.api_enabled(), sa_email=gcal.service_account_email())


@router.post("/perfil")
async def profile(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = await request.form()
    user.phone = str(f.get("phone", "")).strip()
    user.color = str(f.get("color") or user.color)
    db.commit()
    flash(request, "Perfil actualizado.")
    return redirect("/configuracion")


@router.post("/google")
async def google_calendar(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = await request.form()
    user.gcal_calendar_id = str(f.get("gcal_calendar_id", "")).strip()
    db.commit()
    flash(request, "Google Calendar vinculado." if user.gcal_calendar_id else "Google Calendar desvinculado.")
    return redirect("/configuracion#google")


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
    new, confirm = str(f.get("new", "")), str(f.get("confirm", ""))
    if not verify_password(str(f.get("current", "")), user.password_hash):
        flash(request, "La contraseña actual no es correcta.", "error")
    elif len(new) < 6:
        flash(request, "La nueva contraseña debe tener al menos 6 caracteres.", "error")
    elif new != confirm:
        flash(request, "La confirmación no coincide con la nueva contraseña.", "error")
    elif verify_password(new, user.password_hash):
        flash(request, "La nueva contraseña debe ser distinta de la actual.", "error")
    else:
        user.password_hash = hash_password(new)
        db.commit()
        flash(request, "Contraseña actualizada. Úsala la próxima vez que entres.")
    return redirect("/configuracion#seguridad")


PHOTO_PREFIXES = ("data:image/jpeg;base64,", "data:image/png;base64,", "data:image/webp;base64,")
PHOTO_MAX = 400_000


@router.post("/foto")
async def photo(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = await request.form()
    if f.get("quitar"):
        user.photo = ""
        db.commit()
        flash(request, "Foto eliminada.")
        return redirect("/configuracion#perfil")
    data = str(f.get("foto") or "")
    if not data.startswith(PHOTO_PREFIXES) or len(data) > PHOTO_MAX:
        flash(request, "No se pudo leer la imagen. Prueba con una foto JPG o PNG.", "error")
        return redirect("/configuracion#perfil")
    user.photo = data
    db.commit()
    flash(request, "Foto actualizada.")
    return redirect("/configuracion#perfil")
