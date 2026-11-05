from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..utils import verify_password
from ..web import flash, redirect, render

router = APIRouter()


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
    user = db.scalar(select(User).where(User.username == username))
    if not user or not verify_password(str(form.get("password", "")), user.password_hash):
        flash(request, "Usuario o contraseña incorrectos.", "error")
        return redirect("/login")
    request.session.clear()
    request.session["uid"] = user.id
    return redirect("/")


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/login")
