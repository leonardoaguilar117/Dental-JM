from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Patient, Reminder, User
from ..utils import now_local, parse_date, safe_next, to_int
from ..web import current_user, flash, redirect

router = APIRouter(prefix="/recordatorios")


@router.get("")
def list_reminders():
    """La lista de recordatorios vive en Avisos (todo se manda por WhatsApp); los enlaces viejos llegan ahí."""
    return redirect("/avisos")


@router.post("/nuevo")
async def create(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = await request.form()
    due = parse_date(f.get("due_date"))
    pid = to_int(f.get("patient_id"))
    if not due or not pid or not db.get(Patient, pid):
        flash(request, "Paciente y fecha son obligatorios.", "error")
        return redirect("/avisos")
    db.add(Reminder(patient_id=pid, doctor_id=user.id, due_date=due,
                    kind=str(f.get("kind") or "Otro")[:80], message=str(f.get("message", "")).strip()[:500]))
    db.commit()
    flash(request, "Recordatorio creado.")
    return redirect(safe_next(f.get("next"), "/avisos"))


@router.post("/{rid}/{accion}")
async def action(rid: int, accion: str, request: Request, db: Session = Depends(get_db),
                 user: User = Depends(current_user)):
    r = db.get(Reminder, rid)
    if not r or r.doctor_id != user.id:  # cada doctor gestiona solo sus recordatorios
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
    return redirect(safe_next(f.get("next"), "/avisos"))
