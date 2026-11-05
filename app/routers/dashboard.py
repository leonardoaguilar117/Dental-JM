from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Appointment, Patient, Treatment, User
from ..services import finance, inventory, notifications
from ..utils import MESES, add_months, today_local
from ..web import current_user, render

router = APIRouter()


def _parse_month(value: str | None) -> tuple[int, int]:
    t = today_local()
    if value:
        try:
            y, m = value.split("-")
            return int(y), int(m)
        except ValueError:
            pass
    return t.year, t.month


@router.get("/")
def dashboard(request: Request, mes: str | None = None,
              db: Session = Depends(get_db), user: User = Depends(current_user)):
    year, month = _parse_month(mes)
    scope = user  # cada doctor ve solo sus números
    summary = finance.month_summary(db, scope, year, month)
    chart = finance.series(db, scope, year, month, 6)
    receivable_total, receivable_items = finance.receivables(db, scope)

    today = today_local()
    t0 = datetime.combine(today, datetime.min.time())
    q = select(Appointment).where(Appointment.start >= t0, Appointment.start < t0 + timedelta(days=1),
                                  Appointment.status != "cancelada").order_by(Appointment.start)
    if scope is not None:
        q = q.where(Appointment.doctor_id == user.id)
    today_appts = db.scalars(q).all()

    week_q = select(Appointment).where(Appointment.start >= t0 + timedelta(days=1),
                                       Appointment.start < t0 + timedelta(days=8),
                                       Appointment.status != "cancelada")
    if scope is not None:
        week_q = week_q.where(Appointment.doctor_id == user.id)
    upcoming_count = len(db.scalars(week_q).all())

    tq = select(Treatment).where(Treatment.status == "en proceso")
    if scope is not None:
        tq = tq.where(Treatment.doctor_id == user.id)
    active_treatments = sorted(db.scalars(tq).all(), key=lambda t: -t.progress_pct)

    patients_count = len(db.scalars(select(Patient.id).where(Patient.active)).all())
    notif = notifications.build(db, user)
    day = _day_strip(db, user, t0)
    finding = _finding(notif, today_appts, user)
    inv = inventory.alerts(db, user.id) if user.can_inventory else None
    py, pm = add_months(year, month, -1)
    ny, nm = add_months(year, month, 1)

    return render(
        request, "dashboard.html", db, user,
        summary=summary, chart=chart, receivable_total=receivable_total,
        receivable_items=receivable_items[:6], today_appts=today_appts, upcoming_count=upcoming_count,
        active_treatments=active_treatments[:8], patients_count=patients_count, notif=notif, inv=inv,
        year=year, month=month, month_name=MESES[month - 1], vista="mia",
        prev_mes=f"{py}-{pm:02d}", next_mes=f"{ny}-{nm:02d}",
        settlement=None,
        day=day, finding=finding,
        max_cat=max(summary["egresos"]["por_categoria"].values(), default=0),
    )


DAY_START, DAY_END = 8 * 60, 20 * 60  # la jornada del consultorio: 08:00-20:00


def _day_strip(db: Session, user: User, t0: datetime) -> dict:
    """Carriles del día: uno por doctor, con sus citas posicionadas en % de la jornada."""
    appts = db.scalars(select(Appointment).where(Appointment.start >= t0, Appointment.start < t0 + timedelta(days=1))
                       .order_by(Appointment.start)).all()
    span = DAY_END - DAY_START

    def place(a):
        s = max(a.start.hour * 60 + a.start.minute, DAY_START)
        e = min(a.end.hour * 60 + a.end.minute, DAY_END)
        return {"a": a, "left": round(100 * (s - DAY_START) / span, 3), "width": round(100 * max(e - s, 15) / span, 3)}

    doctors = db.scalars(select(User).order_by(User.id)).all()
    doctors.sort(key=lambda d: d.id != user.id)  # mi carril primero
    lanes = [{"name": d.full_name, "short": d.short_name, "color": d.color,
              "slots": [place(a) for a in appts if a.doctor_id == d.id]} for d in doctors]
    from ..utils import now_local
    now = now_local()
    minutes = now.hour * 60 + now.minute
    now_pct = round(100 * (minutes - DAY_START) / span, 3) if DAY_START <= minutes <= DAY_END else None
    return {"lanes": lanes, "now_pct": now_pct, "now": now.strftime("%H:%M"),
            "hours": [(h, round(100 * (h * 60 - DAY_START) / span, 3)) for h in range(8, 21, 2)],
            "count": len([a for a in appts if a.status != "cancelada"])}


def _finding(notif: dict, today_appts, user: User) -> list[str]:
    """Lo que más pide atención hoy, en palabras."""
    out = []
    pending = [a for a in today_appts if a.status in ("programada", "confirmada")]
    if pending:
        out.append(f"{len(pending)} cita{'s' if len(pending) != 1 else ''} por atender hoy")
    overdue = [r for r in notif["reminders"] if r["overdue"]]
    if overdue:
        out.append(f"{len(overdue)} recordatorio{'s' if len(overdue) != 1 else ''} vencido{'s' if len(overdue) != 1 else ''}")
    if notif["confirmations"]:
        n = len(notif["confirmations"])
        out.append(f"{n} cita{'s' if n != 1 else ''} de mañana por confirmar")
    if user.can_inventory and notif["inventory"]["expired"]:
        n = len(notif["inventory"]["expired"])
        out.append(f"{n} lote{'s' if n != 1 else ''} caducado{'s' if n != 1 else ''} en el depósito")
    return out


@router.get("/avisos")
def notifications_center(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return render(request, "notifications.html", db, user, notif=notifications.build(db, user))
