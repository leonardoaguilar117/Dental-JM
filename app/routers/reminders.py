from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Patient, Reminder, User
from ..services import notifications
from ..utils import now_local, parse_date, whatsapp_link
from ..web import current_user, flash, redirect, render

router = APIRouter(prefix="/recordatorios")

KINDS = ["Limpieza semestral", "Ajuste mensual de ortodoncia", "Revisión de retenedores",
         "Revisión / retoque de blanqueamiento", "Control de carillas", "Revisión post-quirúrgica",
         "Seguimiento de valoración (presupuesto)", "Cumpleaños", "Otro"]


@router.get("")
def list_reminders(request: Request, estado: str = "pendiente", db: Session = Depends(get_db),
                   user: User = Depends(current_user)):
    q = select(Reminder).where(Reminder.doctor_id == user.id).order_by(Reminder.due_date)
    if estado != "todos":
        q = q.where(Reminder.status == estado)
    items = db.scalars(q).all()
    links = {r.id: whatsapp_link(r.patient.phone, notifications.reminder_message(r)) for r in items}
    patients = db.scalars(select(Patient).where(Patient.active).order_by(Patient.first_name)).all()
    return render(request, "reminders.html", db, user, items=items, links=links, estado=estado,
                  patients=patients, kinds=KINDS)


@router.post("/nuevo")
async def create(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = await request.form()
    due = parse_date(f.get("due_date"))
    if not due or not f.get("patient_id"):
        flash(request, "Paciente y fecha son obligatorios.", "error")
        return redirect("/recordatorios")
    db.add(Reminder(patient_id=int(f["patient_id"]), doctor_id=user.id, due_date=due,
                    kind=str(f.get("kind") or "Otro"), message=str(f.get("message", "")).strip()))
    db.commit()
    flash(request, "Recordatorio creado.")
    return redirect(str(f.get("next") or "/recordatorios"))


@router.post("/{rid}/{accion}")
async def action(rid: int, accion: str, request: Request, db: Session = Depends(get_db),
                 user: User = Depends(current_user)):
    r = db.get(Reminder, rid)
    if not r:
        raise HTTPException(404)
    f = await request.form()
    mapping = {"enviado": "enviado", "completar": "completado", "descartar": "descartado", "reabrir": "pendiente"}
    if accion not in mapping:
        raise HTTPException(400)
    r.status = mapping[accion]
    if accion == "enviado":
        r.sent_at = now_local()
    db.commit()
    flash(request, f"Recordatorio de {r.patient.full_name} marcado como {r.status}.")
    return redirect(str(f.get("next") or "/recordatorios"))
