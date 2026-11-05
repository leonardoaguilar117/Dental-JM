"""Centro de avisos: lo que el doctor debe atender hoy (recordatorios manuales, confirmaciones, inventario)."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import REMINDER_WINDOW_DAYS
from ..models import Appointment, Payment, Reminder, Treatment, User
from ..utils import fecha, today_local, whatsapp_link
from . import inventory


def reminder_message(r: Reminder) -> str:
    if r.message:
        return r.message
    return (f"Hola {r.patient.first_name}, te saludamos del Consultorio Dental JM de parte de "
            f"{r.doctor.short_name}. Te recordamos que ya corresponde tu {r.kind.lower()}. "
            f"¿Te gustaría agendar tu cita? Responde este mensaje y con gusto te apartamos un horario.")


def confirmation_message(a: Appointment) -> str:
    return (f"Hola {a.patient.first_name}, te recordamos tu cita de {a.type.lower()} con "
            f"{a.doctor.short_name} el {fecha(a.start, 'larga')} a las {a.start:%H:%M} hrs. "
            f"Por favor confírmanos tu asistencia. ¡Gracias!")


def balance_message(t: Treatment) -> str:
    return (f"Hola {t.patient.first_name}, te saludamos del Consultorio Dental JM. Te compartimos que tu "
            f"tratamiento \"{t.name}\" tiene un saldo pendiente de ${t.balance:,.2f}. "
            f"Puedes realizar tu abono en tu próxima visita o por transferencia. ¡Gracias!")


def build(db: Session, user: User) -> dict:
    today = today_local()
    window = today + timedelta(days=REMINDER_WINDOW_DAYS)

    reminders = db.scalars(
        select(Reminder)
        .where(Reminder.doctor_id == user.id, Reminder.status == "pendiente", Reminder.due_date <= window)
        .order_by(Reminder.due_date)
    ).all()
    reminder_items = [
        {"r": r, "overdue": r.due_date < today,
         "wa": whatsapp_link(r.patient.phone, reminder_message(r))}
        for r in reminders
    ]

    tomorrow = today + timedelta(days=1)
    t0 = datetime.combine(tomorrow, datetime.min.time())
    appts = db.scalars(
        select(Appointment)
        .where(Appointment.doctor_id == user.id, Appointment.start >= t0,
               Appointment.start < t0 + timedelta(days=1), Appointment.status == "programada")
        .order_by(Appointment.start)
    ).all()
    confirm_items = [{"a": a, "wa": whatsapp_link(a.patient.phone, confirmation_message(a))} for a in appts]

    # Saldos sin abono en 30 días
    debt_items = []
    for t in db.scalars(select(Treatment).where(Treatment.doctor_id == user.id,
                                                Treatment.status.in_(["en proceso", "terminado"]))).all():
        if t.balance <= 0:
            continue
        last = max((p.date for p in t.payments), default=t.created_at.date())
        if (today - last).days >= 30:
            debt_items.append({"t": t, "days": (today - last).days,
                               "wa": whatsapp_link(t.patient.phone, balance_message(t))})

    inv = inventory.alerts(db, user.id) if user.can_inventory else {"low": [], "expiring": [], "expired": []}

    count = (len(reminder_items) + len(confirm_items) + len(debt_items)
             + len(inv["low"]) + len(inv["expiring"]) + len(inv["expired"]))
    return {
        "reminders": reminder_items,
        "confirmations": confirm_items,
        "debts": debt_items,
        "inventory": inv,
        "count": count,
    }


def count_only(db: Session, user: User) -> int:
    try:
        return build(db, user)["count"]
    except Exception:  # nunca romper la navegación por el contador
        return 0


def payment_message(pay) -> str:
    t = pay.treatment
    rest = (f"Saldo pendiente: ${t.balance:,.2f}." if t.balance > 0 else "Tu tratamiento quedó liquidado.")
    return (f"Hola {pay.patient.first_name}, recibimos tu pago de ${pay.amount:,.2f} ({pay.method.lower()}) "
            f"por {t.name.lower()} el {fecha(pay.date)}. {rest} ¡Gracias! — {pay.doctor.short_name}, Consultorio Dental JM")
