import json
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import config
from ..database import get_db
from ..models import AuditLog, ClinicalNote, MedicalHistory, Patient, Payment, User
from ..utils import (now_local, parse_date, parse_datetime, to_int, valid_data_image, whatsapp_link)
from ..web import current_user, flash, redirect, render
from ..services import audit, notifications, gcal

router = APIRouter(prefix="/pacientes")

PATIENT_FIELDS = ["first_name", "last_name", "sex", "phone", "email", "address", "occupation",
                  "emergency_contact", "notes", "curp", "estado_civil", "lugar_nacimiento"]
PATIENT_MAX = {"first_name": 80, "last_name": 120, "sex": 12, "phone": 20, "email": 120, "address": 255,
               "occupation": 80, "emergency_contact": 160, "notes": 2000, "curp": 18, "estado_civil": 20,
               "lugar_nacimiento": 80}
SEX_OPTIONS = ["Femenino", "Masculino"]
CURP_RE = re.compile(r"^[A-Z]{4}\d{6}[HMX][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$")

HISTORY_TEXT = ["motivo_consulta", "padecimiento_actual", "antecedentes_heredofamiliares",
                "antecedentes_patologicos", "antecedentes_no_patologicos", "alergias", "medicamentos",
                "presion_arterial", "exploracion_extraoral", "exploracion_intraoral", "higiene_oral",
                "oclusion", "diagnostico", "plan_tratamiento", "pronostico", "lengua_notas", "encia_notas",
                "grupo_sanguineo", "habitus_exterior", "frecuencia_cardiaca", "frecuencia_respiratoria",
                "temperatura", "peso", "talla", "exploracion_atm", "indice_placa", "estudios_complementarios"]
HISTORY_MAX = {"presion_arterial": 20, "higiene_oral": 20, "oclusion": 120, "pronostico": 60,
               "grupo_sanguineo": 14, "frecuencia_cardiaca": 12, "frecuencia_respiratoria": 12,
               "temperatura": 12, "peso": 12, "talla": 12, "indice_placa": 60}
HISTORY_CHOICES = {"higiene_oral": ["", "Buena", "Regular", "Mala"],
                   "pronostico": ["", "Favorable", "Reservado", "Desfavorable"],
                   "grupo_sanguineo": config.GRUPOS_SANGUINEOS}
TEXT_MAX = 5000
HISTORY_BOOL = ["diabetes", "hipertension", "cardiopatia", "coagulacion", "embarazo", "fumador",
                "bruxismo", "aviso_privacidad"]  # consentimiento_firmado lo marca la firma en pantalla

SIGNATURE_PREFIX = ("data:image/png;base64,",)
SIGNATURE_MAX = 400_000  # ~300 KB de imagen; una firma normal pesa 10-40 KB
VALID_TEETH = {str(n) for q in (1, 2, 3, 4) for n in range(q * 10 + 1, q * 10 + 9)} | \
              {str(n) for q in (5, 6, 7, 8) for n in range(q * 10 + 1, q * 10 + 6)}


def _get_patient(db: Session, pid: int) -> Patient:
    p = db.get(Patient, pid)
    if not p:
        raise HTTPException(404, "Paciente no encontrado")
    return p


def _clean_odontogram(raw: str) -> str | None:
    """Solo piezas FDI válidas con estados conocidos: un dato corrupto no debe romper las vistas."""
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    return json.dumps({str(k): v for k, v in data.items()
                       if str(k) in VALID_TEETH and v in config.TOOTH_STATES})


def _doctor_id(db: Session, raw, default: int) -> int:
    did = to_int(raw)
    return did if did and db.get(User, did) else default


def _patient_values(f, db: Session, user: User) -> tuple[dict, str | None]:
    vals = {k: str(f.get(k, "")).strip()[:PATIENT_MAX[k]] for k in PATIENT_FIELDS}
    vals["curp"] = vals["curp"].upper()
    if vals["estado_civil"] not in config.ESTADOS_CIVILES:
        vals["estado_civil"] = ""
    if not vals["first_name"] or not vals["last_name"]:
        return vals, "Nombre y apellidos son obligatorios."
    if vals["sex"] not in SEX_OPTIONS:
        return vals, "Elige el sexo del paciente: Femenino o Masculino."
    if vals["curp"] and not CURP_RE.match(vals["curp"]):
        return vals, "La CURP no tiene un formato válido (18 caracteres)."
    return vals, None


@router.get("")
def list_patients(request: Request, q: str = "", doctor: str = "", saldo: str = "",
                  db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(Patient).where(Patient.active).order_by(Patient.last_name, Patient.first_name)
    q = q.strip()[:80]
    if q:
        like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        conds = [Patient.first_name.ilike(like, escape="\\"), Patient.last_name.ilike(like, escape="\\"),
                 Patient.phone.ilike(like, escape="\\"), Patient.email.ilike(like, escape="\\"),
                 Patient.curp.ilike(like, escape="\\")]
        if q.lstrip("#").isdigit():
            conds.append(Patient.id == int(q.lstrip("#")))  # número de expediente
        stmt = stmt.where(or_(*conds))
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
    vals, error = _patient_values(f, db, user)
    if error:
        flash(request, error, "error")
        return redirect("/pacientes/nuevo")
    p = Patient(**vals)
    p.birth_date = parse_date(f.get("birth_date"))
    p.primary_doctor_id = _doctor_id(db, f.get("primary_doctor_id"), user.id)
    db.add(p)
    db.flush()
    db.add(MedicalHistory(patient_id=p.id, updated_by_id=user.id))
    audit.log(db, request, user, "alta", p.id, "Expediente creado")
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
    # el recibo solo se muestra al doctor que cobró (cada doctor ve únicamente sus montos)
    if last_pay and (last_pay.patient_id != p.id or last_pay.doctor_id != user.id):
        last_pay = None
    paid_wa = whatsapp_link(p.phone, notifications.payment_message(last_pay)) if last_pay and p.phone else ""
    audit.log(db, request, user, "consulta", p.id, "Consulta de expediente")
    db.commit()
    trail = db.scalars(select(AuditLog).where(AuditLog.patient_id == p.id, AuditLog.action != "consulta")
                       .order_by(AuditLog.id.desc()).limit(25)).all()
    return render(request, "patients/detail.html", db, user, p=p, h=p.history, doctors=doctors,
                  last_pay=last_pay, paid_wa=paid_wa, tooth_states=config.TOOTH_STATES, reminder_links=reminder_links,
                  tooth_states_json=json.dumps({k: list(v) for k, v in config.TOOTH_STATES.items()}, ensure_ascii=False),
                  gcal_link=gcal.add_link, trail=trail, ESTADOS=config.ESTADOS_CIVILES)


@router.get("/{pid}/editar")
def edit_patient(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    doctors = db.scalars(select(User).order_by(User.id)).all()
    return render(request, "patients/form.html", db, user, p=_get_patient(db, pid), doctors=doctors)


@router.post("/{pid}/editar")
async def update_patient(pid: int, request: Request, db: Session = Depends(get_db),
                         user: User = Depends(current_user)):
    p = _get_patient(db, pid)
    f = await request.form()
    vals, error = _patient_values(f, db, user)
    if error:
        flash(request, error, "error")
        return redirect(f"/pacientes/{pid}/editar")
    changed = [k for k, v in vals.items() if getattr(p, k) != v]
    for k, v in vals.items():
        setattr(p, k, v)
    p.birth_date = parse_date(f.get("birth_date"))
    p.primary_doctor_id = _doctor_id(db, f.get("primary_doctor_id"), p.primary_doctor_id or user.id)
    if changed:
        audit.log(db, request, user, "ficha", p.id, "Campos modificados: " + ", ".join(changed))
    db.commit()
    flash(request, "Datos del paciente actualizados.")
    return redirect(f"/pacientes/{pid}")


@router.post("/{pid}/archivar")
def archive_patient(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _get_patient(db, pid)
    p.active = False
    audit.log(db, request, user, "archivo", p.id, "Expediente archivado (se conserva)")
    db.commit()
    flash(request, f"{p.full_name} fue archivado (su información se conserva).")
    return redirect("/pacientes")


@router.post("/{pid}/historia")
async def save_history(pid: int, request: Request, db: Session = Depends(get_db),
                       user: User = Depends(current_user)):
    p = _get_patient(db, pid)
    h = p.history or MedicalHistory(patient_id=p.id)
    f = await request.form()
    changed = []
    for k in HISTORY_TEXT:
        v = str(f.get(k, "")).strip()[:HISTORY_MAX.get(k, TEXT_MAX)]
        if k in HISTORY_CHOICES and v not in HISTORY_CHOICES[k]:
            v = ""
        if (getattr(h, k) or "") != v:
            changed.append(k)
        setattr(h, k, v)
    for k in HISTORY_BOOL:
        new = f.get(k) == "on"
        if k == "aviso_privacidad" and new and not h.aviso_privacidad:
            h.aviso_privacidad_fecha = now_local()
        if bool(getattr(h, k)) != new:
            changed.append(k)
        setattr(h, k, new)
    aparatos = {key: str(f.get(f"ap_{key}", "")).strip()[:500] for key, _ in config.APARATOS}
    new_ap = json.dumps({k: v for k, v in aparatos.items() if v}, ensure_ascii=False)
    if new_ap != (h.aparatos_json or "{}"):
        changed.append("aparatos_y_sistemas")
    h.aparatos_json = new_ap
    h.lengua_hallazgos = json.dumps([x for x in f.getlist("lengua") if x in config.LENGUA_OPCIONES], ensure_ascii=False)
    h.encia_hallazgos = json.dumps([x for x in f.getlist("encia") if x in config.ENCIA_OPCIONES], ensure_ascii=False)
    odo = _clean_odontogram(str(f.get("odontograma_json") or "{}"))
    if odo is not None:
        if odo != (h.odontograma_json or "{}"):
            changed.append("odontograma")
        h.odontograma_json = odo
    h.updated_at = now_local()
    h.updated_by_id = user.id
    db.add(h)
    audit.log(db, request, user, "historia", p.id,
              "Historia clínica guardada. Cambios: " + (", ".join(changed) or "ninguno"))
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
    acto = str(f.get("acto") or "").strip()[:TEXT_MAX]
    riesgos = str(f.get("riesgos") or "").strip()[:TEXT_MAX]
    calidad = str(f.get("calidad") or "Paciente")
    if calidad not in config.CALIDADES_CONSENTIMIENTO:
        calidad = "Paciente"
    if not valid_data_image(firma, SIGNATURE_PREFIX, SIGNATURE_MAX):
        flash(request, "No se recibió la firma. Pide al paciente que firme en el recuadro.", "error")
        return redirect(f"/pacientes/{pid}#historia")
    if not acto or not riesgos:
        flash(request, "Indica el acto médico autorizado y sus riesgos y beneficios antes de firmar.", "error")
        return redirect(f"/pacientes/{pid}#historia")
    h = p.history or MedicalHistory(patient_id=p.id)
    h.consentimiento_firma = firma
    h.consentimiento_nombre = nombre[:160]
    h.consentimiento_calidad = calidad
    h.consentimiento_acto = acto
    h.consentimiento_riesgos = riesgos
    h.consentimiento_testigo1 = str(f.get("testigo1") or "").strip()[:160]
    h.consentimiento_testigo2 = str(f.get("testigo2") or "").strip()[:160]
    h.consentimiento_fecha = now_local()
    h.consentimiento_firmado = True
    h.updated_by_id = user.id
    db.add(h)
    audit.log(db, request, user, "consentimiento", p.id, f"Consentimiento firmado por {h.consentimiento_nombre} ({calidad})")
    db.commit()
    flash(request, f"Consentimiento informado firmado por {h.consentimiento_nombre}.")
    return redirect(f"/pacientes/{pid}#historia")


@router.post("/{pid}/consentimiento/eliminar")
def clear_consent(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _get_patient(db, pid)
    h = p.history
    if h:
        audit.log(db, request, user, "consentimiento", p.id,
                  f"Firma eliminada (había firmado {h.consentimiento_nombre or 'en papel'}"
                  f"{', ' + h.consentimiento_fecha.strftime('%d/%m/%Y %H:%M') if h.consentimiento_fecha else ''})")
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
    now = now_local()
    when = parse_datetime(f.get("date")) or now
    kind = str(f.get("kind") or "Evolución")
    note = ClinicalNote(
        patient_id=pid, doctor_id=user.id, date=min(when, now),  # una nota no puede fecharse en el futuro
        kind=kind if kind in config.NOTE_KINDS else "Evolución",
        procedure=str(f.get("procedure", "")).strip()[:160], teeth=str(f.get("teeth", "")).strip()[:80],
        note=str(f.get("note", "")).strip()[:TEXT_MAX], next_step=str(f.get("next_step", "")).strip()[:255],
        vitals=str(f.get("vitals", "")).strip()[:160], diagnosis=str(f.get("diagnosis", "")).strip()[:255],
        studies=str(f.get("studies", "")).strip()[:TEXT_MAX], indications=str(f.get("indications", "")).strip()[:TEXT_MAX],
    )
    if not note.note and not note.procedure:
        flash(request, "La nota está vacía.", "error")
    else:
        db.add(note)
        audit.log(db, request, user, "nota", pid, f"Nota agregada ({note.kind})")
        db.commit()
        flash(request, "Nota agregada al expediente. Las notas no se editan: corrige con una nota aclaratoria.")
    return redirect(f"/pacientes/{pid}#evolucion")


@router.get("/{pid}/historia/imprimir")
def print_history(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _get_patient(db, pid)
    audit.log(db, request, user, "impresion", p.id, "Historia clínica impresa")
    db.commit()
    return render(request, "patients/print.html", db, user, p=p, h=p.history or MedicalHistory(patient_id=p.id),
                  tooth_states=config.TOOTH_STATES)


@router.get("/{pid}/consentimiento/imprimir")
def print_consent(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _get_patient(db, pid)
    audit.log(db, request, user, "impresion", p.id, "Consentimiento informado impreso")
    db.commit()
    return render(request, "patients/consent.html", db, user, p=p, h=p.history or MedicalHistory(patient_id=p.id))
