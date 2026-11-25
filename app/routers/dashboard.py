from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Appointment, User
from ..services import finance, inventory, notifications
from ..utils import DIAS, MESES, fecha, today_local
from ..web import current_user, render

router = APIRouter()


@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Inicio: el día del consultorio. Las finanzas viven en /finanzas."""
    from ..utils import now_local, whatsapp_link
    today = today_local()
    now = now_local().replace(tzinfo=None)
    t0 = datetime.combine(today, datetime.min.time())
    q = select(Appointment).where(Appointment.start >= t0, Appointment.start < t0 + timedelta(days=1),
                                  Appointment.status != "cancelada", Appointment.doctor_id == user.id
                                  ).order_by(Appointment.start)
    today_appts = db.scalars(q).all()
    open_states = ("programada", "confirmada")
    # pendientes de hoy: las que aún no terminan (por atender) y las que ya pasaron sin cerrarse (sin marcar)
    to_attend = [a for a in today_appts if a.status in open_states and a.end >= now]
    unmarked = [a for a in today_appts if a.status in open_states and a.end < now]

    week_q = select(Appointment).where(Appointment.start >= t0 + timedelta(days=1),
                                       Appointment.start < t0 + timedelta(days=8),
                                       Appointment.status != "cancelada", Appointment.doctor_id == user.id)
    week_appts = db.scalars(week_q.order_by(Appointment.start)).all()

    # próxima cita: la siguiente de hoy que aún no termina; si ya no hay, la primera de los próximos días
    next_appt = to_attend[0] if to_attend else (week_appts[0] if week_appts else None)
    next_wa = None
    if next_appt and next_appt.patient.phone:
        next_wa = whatsapp_link(next_appt.patient.phone,
                                f"Hola {next_appt.patient.first_name}, te esperamos el {fecha(next_appt.start, 'larga')} "
                                f"a las {next_appt.start:%H:%M} en el Consultorio Dental JM.")

    # tira de la semana: hoy y los días siguientes (sin domingo, el consultorio no abre)
    counts = {}
    for a in [*today_appts, *week_appts]:
        counts[a.start.date()] = counts.get(a.start.date(), 0) + 1
    week = []
    d = today
    while len(week) < 6:
        if d.weekday() != 6:
            week.append({"date": d, "dow": DIAS[d.weekday()][:3], "n": counts.get(d, 0), "today": d == today})
        d += timedelta(days=1)

    notif = notifications.build(db, user)
    # avisos por mandar: vencidos primero, luego confirmaciones de mañana y los próximos
    reminders = sorted(notif["reminders"], key=lambda x: (not x["overdue"], x["r"].due_date))
    feed = [{"kind": "rem", "id": x["r"].id, "p": x["r"].patient, "what": x["r"].kind, "late": x["overdue"],
             "when": x["r"].due_date, "wa": x["wa"] if x["r"].patient.phone else None} for x in reminders if x["overdue"]]
    feed += [{"kind": "conf", "id": x["a"].id, "p": x["a"].patient, "what": x["a"].type, "late": False, "when": x["a"].start,
              "wa": x["wa"] if x["a"].patient.phone else None} for x in notif["confirmations"]]
    feed += [{"kind": "rem", "id": x["r"].id, "p": x["r"].patient, "what": x["r"].kind, "late": False,
              "when": x["r"].due_date, "wa": x["wa"] if x["r"].patient.phone else None} for x in reminders if not x["overdue"]]

    receivable_total, _ = finance.receivables(db, user)
    summary = finance.month_summary(db, user, today.year, today.month)
    inv = inventory.alerts(db, user.id) if user.can_inventory else None
    return render(
        request, "dashboard.html", db, user,
        today_appts=today_appts, to_attend=to_attend, unmarked=unmarked,
        upcoming_count=len(to_attend) + len(week_appts), next_appt=next_appt, next_wa=next_wa, week=week,
        feed=feed, notif=notif, inv=inv, receivable_total=receivable_total, summary=summary,
        month_name=MESES[today.month - 1], day=_day_strip(db, user, t0),
        finding=_finding(notif, to_attend, unmarked, user),
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


def _finding(notif: dict, to_attend, unmarked, user: User) -> list[dict]:
    """Lo que más pide atención hoy, en palabras y con a dónde ir."""
    out = []
    if to_attend:
        n = len(to_attend)
        out.append({"t": f"{n} cita{'s' if n != 1 else ''} por atender hoy", "href": "/agenda", "hot": True})
    if unmarked:
        n = len(unmarked)
        out.append({"t": f"{n} cita{'s' if n != 1 else ''} de hoy sin marcar", "href": f"/citas/{unmarked[0].id}", "hot": False})
    overdue = [r for r in notif["reminders"] if r["overdue"]]
    if overdue:
        n = len(overdue)
        out.append({"t": f"{n} recordatorio{'s' if n != 1 else ''} vencido{'s' if n != 1 else ''}", "href": "#avisos", "hot": False})
    if notif["confirmations"]:
        n = len(notif["confirmations"])
        out.append({"t": f"{n} cita{'s' if n != 1 else ''} de mañana por confirmar", "href": "#avisos", "hot": False})
    if user.can_inventory and notif["inventory"]["expired"]:
        n = len(notif["inventory"]["expired"])
        out.append({"t": f"{n} lote{'s' if n != 1 else ''} caducado{'s' if n != 1 else ''} en el depósito", "href": "/inventario?filtro=caducados", "hot": False})
    return out


@router.get("/avisos")
def notifications_center(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return render(request, "notifications.html", db, user, notif=notifications.build(db, user))
