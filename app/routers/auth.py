import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..utils import hash_password, verify_password
from ..web import flash, redirect, render

router = APIRouter()

# Freno a la fuerza bruta: 5 fallos por usuario+IP bloquean 10 minutos (en memoria; suficiente para una instancia)
MAX_FAILS, LOCK_SECONDS = 5, 600
_fails: dict[tuple[str, str], tuple[int, float]] = {}
_DUMMY_HASH = hash_password("sin-usuario")


def _locked(key: tuple[str, str]) -> bool:
    n, ts = _fails.get(key, (0, 0.0))
    if n >= MAX_FAILS and time.time() - ts < LOCK_SECONDS:
        return True
    if n >= MAX_FAILS:
        _fails.pop(key, None)
    return False


@router.get("/login")
def login_form(request: Request, db: Session = Depends(get_db)):
    if request.session.get("uid"):
        return redirect("/")
    doctors = db.scalars(select(User).order_by(User.id)).all()
    return render(request, "login.html", db, None, doctors=doctors)


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = str(form.get("username", "")).strip().lower()
    key = (request.client.host if request.client else "", username[:50])
    if _locked(key):
        flash(request, "Demasiados intentos fallidos. Espera 10 minutos e inténtalo de nuevo.", "error")
        return redirect("/login")
    user = db.scalar(select(User).where(User.username == username))
    # siempre se calcula un hash (aunque el usuario no exista) para no revelar qué usuarios existen
    ok = verify_password(str(form.get("password", ""))[:200], user.password_hash if user else _DUMMY_HASH)
    if not user or not ok:
        n, _ = _fails.get(key, (0, 0.0))
        _fails[key] = (n + 1, time.time())
        flash(request, "Usuario o contraseña incorrectos.", "error")
        return redirect("/login")
    _fails.pop(key, None)
    request.session.clear()
    request.session["uid"] = user.id
    return redirect("/")


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/login")
