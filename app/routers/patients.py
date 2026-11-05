import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import config
from ..database import get_db
from ..models import ClinicalNote, ExternalSpecialist, MedicalHistory, Patient, User
from ..utils import now_local, parse_date, parse_datetime
from ..web import current_user, flash, redirect, render
from ..services import notifications, gcal

router = APIRouter(prefix="/pacientes")

PATIENT_FIELDS = ["first_name", "last_name", "sex", "phone", "email", "address", "occupation",
                  "emergency_contact", "referred_by", "notes"]
HISTORY_TEXT = ["motivo_consulta", "padecimiento_actual", "antecedentes_heredofamiliares",
                "antecedentes_patologicos", "antecedentes_no_patologicos", "alergias", "medicamentos",
                "presion_arterial", "exploracion_extraoral", "exploracion_intraoral", "higiene_oral",
                "oclusion", "diagnostico", "plan_tratamiento", "pronostico"]
HISTORY_BOOL = ["diabetes", "hipertension", "cardiopatia", "coagulacion", "embarazo", "fumador",
                "bruxismo", "consentimiento_firmado", "aviso_privacidad"]


def _get_patient(db: Session, pid: int) -> Patient:
    p = db.get(Patient, pid)
    if not p:
        raise HTTPException(404, "Paciente no encontrado")
    return p


@router.get("")
def list_patients(request: Request, q: str = "", doctor: str = "", saldo: str = "",
                  db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(Patient).where(Patient.active).order_by(Patient.last_name, Patient.first_name)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Patient.first_name.ilike(like), Patient.last_name.ilike(like),
                              Patient.phone.ilike(like), Patient.email.ilike(like)))
    if doctor.isdigit():
        stmt = stmt.where(Patient.primary_doctor_id == int(doctor))
    patients = db.scalars(stmt).all()
    if saldo:
        patients = [p for p in patients if p.balance > 0]
    doctors = db.scalars(select(User).order_by(User.id)).all()
    return render(request, "patients/list.html", db, user, patients=patients, q=q, doctor=doctor,
                  saldo=saldo, doctors=doctors)


@router.get("/nuevo")
def new_patient(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    doctors = db.scalars(select(User).order_by(User.id)).all()
    return render(request, "patients/form.html", db, user, p=None, doctors=doctors)


@router.post("/nuevo")
async def create_patient(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = await request.form()
    p = Patient(**{k: str(f.get(k, "")).strip() for k in PATIENT_FIELDS})
    p.birth_date = parse_date(f.get("birth_date"))
    p.primary_doctor_id = int(f.get("primary_doctor_id") or user.id)
    if not p.first_name or not p.last_name:
        flash(request, "Nombre y apellidos son obligatorios.", "error")
        return redirect("/pacientes/nuevo")
    db.add(p)
    db.flush()
    db.add(MedicalHistory(patient_id=p.id, updated_by_id=user.id))
    db.commit()
    flash(request, f"Paciente {p.full_name} registrado. Completa su historia clínica.")
    return redirect(f"/pacientes/{p.id}#historia")


@router.get("/{pid}")
def patient_detail(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _get_patient(db, pid)
    if not p.history:
        db.add(MedicalHistory(patient_id=p.id, updated_by_id=user.id))
        db.commit()
        db.refresh(p)
    doctors = db.scalars(select(User).order_by(User.id)).all()
    externals = db.scalars(select(ExternalSpecialist).where(ExternalSpecialist.active)).all()
    reminder_links = {r.id: notifications.reminder_message(r) for r in p.reminders}
    return render(request, "patients/detail.html", db, user, p=p, h=p.history, doctors=doctors,
                  externals=externals, tooth_states=config.TOOTH_STATES, reminder_links=reminder_links,
                  tooth_states_json=json.dumps({k: list(v) for k, v in config.TOOTH_STATES.items()}, ensure_ascii=False),
                  gcal_link=gcal.add_link)


@router.get("/{pid}/editar")
def edit_patient(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    doctors = db.scalars(select(User).order_by(User.id)).all()
    return render(request, "patients/form.html", db, user, p=_get_patient(db, pid), doctors=doctors)


@router.post("/{pid}/editar")
async def update_patient(pid: int, request: Request, db: Session = Depends(get_db),
                         user: User = Depends(current_user)):
    p = _get_patient(db, pid)
    f = await request.form()
    for k in PATIENT_FIELDS:
        setattr(p, k, str(f.get(k, "")).strip())
    p.birth_date = parse_date(f.get("birth_date"))
    p.primary_doctor_id = int(f.get("primary_doctor_id") or user.id)
    db.commit()
    flash(request, "Datos del paciente actualizados.")
    return redirect(f"/pacientes/{pid}")


@router.post("/{pid}/archivar")
def archive_patient(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _get_patient(db, pid)
    p.active = False
    db.commit()
    flash(request, f"{p.full_name} fue archivado (su información se conserva).")
    return redirect("/pacientes")


@router.post("/{pid}/historia")
async def save_history(pid: int, request: Request, db: Session = Depends(get_db),
                       user: User = Depends(current_user)):
    p = _get_patient(db, pid)
    h = p.history or MedicalHistory(patient_id=p.id)
    f = await request.form()
    for k in HISTORY_TEXT:
        setattr(h, k, str(f.get(k, "")).strip())
    for k in HISTORY_BOOL:
        setattr(h, k, f.get(k) == "on")
    odo = str(f.get("odontograma_json") or "{}")
    try:
        json.loads(odo)
        h.odontograma_json = odo
    except ValueError:
        pass
    h.updated_at = now_local()
    h.updated_by_id = user.id
    db.add(h)
    db.commit()
    flash(request, "Historia clínica guardada.")
    return redirect(f"/pacientes/{pid}#historia")


@router.post("/{pid}/notas")
async def add_note(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _get_patient(db, pid)
    f = await request.form()
    note = ClinicalNote(
        patient_id=pid, doctor_id=user.id, date=parse_datetime(f.get("date")) or now_local(),
        procedure=str(f.get("procedure", "")).strip(), teeth=str(f.get("teeth", "")).strip(),
        note=str(f.get("note", "")).strip(), next_step=str(f.get("next_step", "")).strip(),
    )
    if not note.note and not note.procedure:
        flash(request, "La nota está vacía.", "error")
    else:
        db.add(note)
        db.commit()
        flash(request, "Nota de evolución agregada.")
    return redirect(f"/pacientes/{pid}#evolucion")


@router.get("/{pid}/historia/imprimir")
def print_history(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _get_patient(db, pid)
    return render(request, "patients/print.html", db, user, p=p, h=p.history, tooth_states=config.TOOTH_STATES)
