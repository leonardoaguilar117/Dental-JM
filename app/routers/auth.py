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
    import json
    from .. import config
    return render(request, "login.html", db, None, doctors=doctors,
                  tooth_states_json=json.dumps({k: list(v) for k, v in config.TOOTH_STATES.items()}, ensure_ascii=False))


def _arch() -> list[dict]:
    """Arco dental (32 piezas FDI) para la ilustración del acceso: posición, giro y estado de cada pieza."""
    import math

    states = {"16": "#0ea1d2", "26": "#0ea1d2", "36": "#c4242a", "12": "#0ea1d2",
              "46": "#6c4813", "38": "#1c2030", "48": "#1c2030"}
    brackets = {str(t) for t in [13, 12, 22, 23, 33, 32, 31, 41, 42, 43, 14, 24, 34, 44, 15, 25, 35, 45]}
    teeth = []
    for jaw, (cy, sign) in enumerate([(205, -1), (215, 1)]):
        right = [18, 17, 16, 15, 14, 13, 12, 11] if jaw == 0 else [48, 47, 46, 45, 44, 43, 42, 41]
        left = [21, 22, 23, 24, 25, 26, 27, 28] if jaw == 0 else [31, 32, 33, 34, 35, 36, 37, 38]
        order = right + left
        for i, num in enumerate(order):
            a = math.pi * (0.06 + 0.88 * i / (len(order) - 1))  # de izquierda a derecha
            x = 280 - 230 * math.cos(a)
            y = cy + sign * 150 * math.sin(a)
            rot = math.degrees(math.atan2(-math.cos(a) * 150, math.sin(a) * 230)) * -sign
            k = str(num)
            fill = states.get(k, "#ffffff")
            teeth.append({"x": round(x, 1), "y": round(y, 1), "r": round(-rot if jaw == 0 else rot, 1), "fill": fill,
                          "bracket": k in brackets and fill == "#ffffff", "n": k, "w": 30 if num % 10 >= 6 else 24})
    return teeth


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
