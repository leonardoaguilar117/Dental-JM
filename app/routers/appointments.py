from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..database import get_db
from ..models import Appointment, ClinicalNote, ExternalSpecialist, Patient, Reminder, Treatment, User
from ..services import gcal, notifications
from ..utils import fecha, now_local, parse_datetime, whatsapp_link
from ..web import current_user, flash, redirect, render

router = APIRouter()


def _conflicts(db: Session, start: datetime, end: datetime, doctor_id: int, external_id: int | None,
               exclude_id: int | None = None) -> list[str]:
    q = select(Appointment).where(Appointment.status.notin_(["cancelada", "no asistió"]),
                                  Appointment.start < end, Appointment.end > start)
    if exclude_id:
        q = q.where(Appointment.id != exclude_id)
    msgs = []
    for a in db.scalars(q).all():
        if a.doctor_id == doctor_id:
            msgs.append(f"{a.doctor.short_name} ya tiene cita de {a.start:%H:%M} a {a.end:%H:%M} "
                        f"({a.patient.full_name}).")
        if external_id and a.external_id == external_id:
            msgs.append(f"{a.external.full_name} ya está agendado de {a.start:%H:%M} a {a.end:%H:%M} "
                        f"con {a.doctor.short_name}.")
    return msgs


def _tint(hex_color: str, amount: float) -> str:
    """Mezcla un color con blanco (tono pálido para el fondo de los eventos)."""
    h = hex_color.lstrip("#")
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return "#eef0f4"
    mix = lambda c: round(255 - (255 - c) * amount)
    return f"#{mix(r):02x}{mix(g):02x}{mix(b):02x}"


def _form_ctx(db: Session):
    return dict(
        doctors=db.scalars(select(User).order_by(User.id)).all(),
        externals=db.scalars(select(ExternalSpecialist).where(ExternalSpecialist.active)).all(),
        patients=db.scalars(select(Patient).where(Patient.active).order_by(Patient.first_name)).all(),
        types=config.APPOINTMENT_TYPES,
        statuses=config.APPOINTMENT_STATUSES,
    )


@router.get("/agenda")
def agenda(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return render(request, "appointments/calendar.html", db, user, **_form_ctx(db))


@router.get("/api/citas")
def api_events(start: str, end: str, doctores: str = "", externo: str = "1",
               db: Session = Depends(get_db), user: User = Depends(current_user)):
    s, e = parse_datetime(start), parse_datetime(end)
    q = select(Appointment).where(Appointment.start < e, Appointment.end > s)
    ids = [int(x) for x in doctores.split(",") if x.isdigit()]
    if ids:
        q = q.where(Appointment.doctor_id.in_(ids))
    events = []
    for a in db.scalars(q).all():
        if externo == "0" and a.external_id:
            continue
        color = a.external.color if a.external else a.doctor.color
        tint = _tint(color, 0.2)
        title = f"{a.patient.full_name} · {a.type}"
        if a.external:
            title = f"{title} · con {a.external.full_name}"
        events.append({
            "id": a.id, "title": title, "start": a.start.isoformat(), "end": a.end.isoformat(),
            "url": f"/citas/{a.id}", "backgroundColor": tint, "borderColor": color, "textColor": "#1c2030",
            "classNames": [f"st-{a.status.replace(' ', '-').replace('ó', 'o')}"],
            "extendedProps": {"status": a.status, "doctor": a.doctor.short_name},
        })
    return JSONResponse(events)


@router.get("/citas/nueva")
def new_appointment(request: Request, start: str = "", paciente: int | None = None,
                    db: Session = Depends(get_db), user: User = Depends(current_user)):
    s = parse_datetime(start) or (now_local().replace(minute=0, second=0) + timedelta(hours=1))
    if s.hour == 0 and s.minute == 0:
        s = s.replace(hour=10)
    return render(request, "appointments/form.html", db, user, a=None, start=s, patient_id=paciente,
                  **_form_ctx(db))


@router.post("/citas/nueva")
async def create_appointment(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = await request.form()
    start = parse_datetime(f.get("start"))
    duration = int(f.get("duration") or 60)
    if not start or not f.get("patient_id"):
        flash(request, "Selecciona paciente, fecha y hora.", "error")
        return redirect("/citas/nueva")
    end = start + timedelta(minutes=duration)
    doctor_id = int(f.get("doctor_id") or user.id)
    external_id = int(f["external_id"]) if f.get("external_id") else None
    conflicts = _conflicts(db, start, end, doctor_id, external_id)
    if conflicts and f.get("force") != "1":
        flash(request, "Conflicto de horario: " + " ".join(conflicts) +
              " Marca «Agendar de todos modos» si es intencional.", "error")
        return render(request, "appointments/form.html", db, user, a=None, start=start,
                      patient_id=int(f.get("patient_id")), prefill=dict(f), **_form_ctx(db))
    a = Appointment(patient_id=int(f["patient_id"]), doctor_id=doctor_id, external_id=external_id,
                    start=start, end=end, type=str(f.get("type") or "Valoración"),
                    notes=str(f.get("notes", "")).strip(), status="programada")
    db.add(a)
    db.flush()
    db.refresh(a)
    ev = gcal.sync(a, a.doctor)
    if ev:
        a.gcal_event_id = ev
    db.commit()
    flash(request, f"Cita agendada para {fecha(a.start, 'larga')} a las {a.start:%H:%M}.")
    return redirect(f"/citas/{a.id}")


@router.get("/citas/{aid}")
def appointment_detail(aid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    a = db.get(Appointment, aid)
    if not a:
        raise HTTPException(404)
    wa_confirm = whatsapp_link(a.patient.phone, notifications.confirmation_message(a))
    treatments = [t for t in a.patient.treatments if t.status in ("presupuesto", "en proceso")]
    return render(request, "appointments/detail.html", db, user, a=a, wa_confirm=wa_confirm, gcal_link=gcal.add_link(a),
                  treatments=treatments, rules=config.REMINDER_RULES, **_form_ctx(db))


@router.post("/citas/{aid}")
async def update_appointment(aid: int, request: Request, db: Session = Depends(get_db),
                             user: User = Depends(current_user)):
    a = db.get(Appointment, aid)
    if not a:
        raise HTTPException(404)
    f = await request.form()
    start = parse_datetime(f.get("start")) or a.start
    duration = int(f.get("duration") or a.duration_min)
    end = start + timedelta(minutes=duration)
    doctor_id = int(f.get("doctor_id") or a.doctor_id)
    external_id = int(f["external_id"]) if f.get("external_id") else None
    conflicts = _conflicts(db, start, end, doctor_id, external_id, exclude_id=a.id)
    if conflicts and f.get("force") != "1":
        flash(request, "Conflicto de horario: " + " ".join(conflicts), "error")
        return redirect(f"/citas/{aid}")
    a.start, a.end, a.doctor_id, a.external_id = start, end, doctor_id, external_id
    a.type = str(f.get("type") or a.type)
    a.notes = str(f.get("notes", "")).strip()
    db.flush()
    db.refresh(a)
    ev = gcal.sync(a, a.doctor)
    if ev:
        a.gcal_event_id = ev
    db.commit()
    flash(request, "Cita actualizada.")
    return redirect(f"/citas/{aid}")


@router.post("/citas/{aid}/estado")
async def change_status(aid: int, request: Request, db: Session = Depends(get_db),
                        user: User = Depends(current_user)):
    """Cambio de estado. Al marcar 'atendida' se registra nota, avance de tratamiento y recordatorio."""
    a = db.get(Appointment, aid)
    if not a:
        raise HTTPException(404)
    f = await request.form()
    status = str(f.get("status"))
    if status not in config.APPOINTMENT_STATUSES:
        raise HTTPException(400)
    a.status = status
    msgs = [f"Cita marcada como «{status}»."]
    if status == "atendida":
        note_text = str(f.get("note", "")).strip()
        if note_text:
            db.add(ClinicalNote(patient_id=a.patient_id, doctor_id=a.doctor_id, appointment_id=a.id,
                                date=a.start, procedure=a.type, note=note_text,
                                teeth=str(f.get("teeth", "")).strip(),
                                next_step=str(f.get("next_step", "")).strip()))
            msgs.append("Nota de evolución guardada.")
        tid = f.get("treatment_id")
        if tid:
            t = db.get(Treatment, int(tid))
            if t:
                t.sessions_done = min(t.sessions_done + 1, max(t.sessions_planned, t.sessions_done + 1))
                if t.status == "presupuesto":
                    t.status = "en proceso"
                if t.sessions_done >= t.sessions_planned:
                    t.status = "terminado"
                msgs.append(f"Avance de «{t.name}»: {t.sessions_done}/{t.sessions_planned} sesiones.")
        if f.get("create_reminder") == "on":
            days = int(f.get("reminder_days") or 0)
            if days > 0:
                kind = config.REMINDER_RULES.get(a.type, (days, f"Seguimiento de {a.type.lower()}"))[1]
                db.add(Reminder(patient_id=a.patient_id, doctor_id=a.doctor_id,
                                due_date=a.start.date() + timedelta(days=days), kind=kind, auto=True))
                msgs.append(f"Recordatorio programado en {days} días.")
    db.flush()
    db.refresh(a)
    ev = gcal.sync(a, a.doctor)
    if ev is not None:
        a.gcal_event_id = ev
    db.commit()
    flash(request, " ".join(msgs))
    return redirect(str(f.get("next") or f"/citas/{aid}"))


@router.get("/calendario/{token}.ics")
def ics_feed(token: str, db: Session = Depends(get_db)):
    """Feed privado para suscribirse desde Google Calendar (no requiere sesión, sí el token)."""
    user = db.scalar(select(User).where(User.ical_token == token)) if token else None
    if not user:
        raise HTTPException(404)
    since = now_local() - timedelta(days=60)
    appts = db.scalars(select(Appointment).where(Appointment.doctor_id == user.id,
                                                 Appointment.start >= since)).all()
    return Response(gcal.ics_feed(user, appts), media_type="text/calendar; charset=utf-8")
