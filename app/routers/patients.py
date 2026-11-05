import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import config
from ..database import get_db
from ..models import ClinicalNote, MedicalHistory, Patient, Payment, User
from ..utils import now_local, parse_date, parse_datetime, whatsapp_link
from ..web import current_user, flash, redirect, render
from ..services import notifications, gcal

router = APIRouter(prefix="/pacientes")

PATIENT_FIELDS = ["first_name", "last_name", "sex", "phone", "email", "address", "occupation",
                  "emergency_contact", "notes"]
HISTORY_TEXT = ["motivo_consulta", "padecimiento_actual", "antecedentes_heredofamiliares",
                "antecedentes_patologicos", "antecedentes_no_patologicos", "alergias", "medicamentos",
                "presion_arterial", "exploracion_extraoral", "exploracion_intraoral", "higiene_oral",
                "oclusion", "diagnostico", "plan_tratamiento", "pronostico", "lengua_notas", "encia_notas"]
HISTORY_BOOL = ["diabetes", "hipertension", "cardiopatia", "coagulacion", "embarazo", "fumador",
                "bruxismo", "aviso_privacidad"]  # consentimiento_firmado lo marca la firma en pantalla

SIGNATURE_PREFIX = "data:image/png;base64,"
SIGNATURE_MAX = 400_000  # ~300 KB de imagen; una firma normal pesa 10-40 KB


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
        patients = [p for p in patients if p.balance_for(user.id) > 0]
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
    reminder_links = {r.id: notifications.reminder_message(r) for r in p.reminders}
    rid = request.query_params.get("recibo", "")
    last_pay = db.get(Payment, int(rid)) if rid.isdigit() else None
    if last_pay and last_pay.patient_id != p.id:
        last_pay = None
    paid_wa = whatsapp_link(p.phone, notifications.payment_message(last_pay)) if last_pay and p.phone else ""
    return render(request, "patients/detail.html", db, user, p=p, h=p.history, doctors=doctors,
                  last_pay=last_pay, paid_wa=paid_wa, tooth_states=config.TOOTH_STATES, reminder_links=reminder_links,
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
    h.lengua_hallazgos = json.dumps([x for x in f.getlist("lengua") if x in config.LENGUA_OPCIONES], ensure_ascii=False)
    h.encia_hallazgos = json.dumps([x for x in f.getlist("encia") if x in config.ENCIA_OPCIONES], ensure_ascii=False)
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


@router.post("/{pid}/consentimiento")
async def sign_consent(pid: int, request: Request, db: Session = Depends(get_db),
                       user: User = Depends(current_user)):
    p = _get_patient(db, pid)
    f = await request.form()
    firma = str(f.get("firma") or "")
    nombre = str(f.get("nombre") or "").strip() or p.full_name
    if not firma.startswith(SIGNATURE_PREFIX) or len(firma) > SIGNATURE_MAX:
        flash(request, "No se recibió la firma. Pide al paciente que firme en el recuadro.", "error")
        return redirect(f"/pacientes/{pid}#historia")
    h = p.history or MedicalHistory(patient_id=p.id)
    h.consentimiento_firma = firma
    h.consentimiento_nombre = nombre[:160]
    h.consentimiento_fecha = now_local()
    h.consentimiento_firmado = True
    h.updated_by_id = user.id
    db.add(h)
    db.commit()
    flash(request, f"Consentimiento informado firmado por {h.consentimiento_nombre}.")
    return redirect(f"/pacientes/{pid}#historia")


@router.post("/{pid}/consentimiento/eliminar")
def clear_consent(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _get_patient(db, pid)
    h = p.history
    if h:
        h.consentimiento_firma = ""
        h.consentimiento_nombre = ""
        h.consentimiento_fecha = None
        h.consentimiento_firmado = False
        h.updated_by_id = user.id
        db.commit()
    flash(request, "Firma eliminada. El paciente puede firmar de nuevo.")
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
