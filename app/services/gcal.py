"""Integración con Google Calendar.

Tres niveles (de menor a mayor configuración):
1. Enlace "Añadir a Google Calendar" por cita (sin configuración).
2. Feed iCal privado por doctor (/calendario/<token>.ics) que Google Calendar puede suscribir
   ("Otros calendarios > Desde URL"). Sincroniza en un solo sentido; Google lo refresca cada varias horas.
3. Sincronización directa vía Google Calendar API con una cuenta de servicio:
   - Definir GOOGLE_SERVICE_ACCOUNT_JSON (contenido JSON de la llave).
   - Cada doctor comparte su calendario con el correo de la cuenta de servicio
     ("Hacer cambios en eventos") y pega el ID del calendario en Configuración.
   Al crear/editar/cancelar una cita, el evento se crea/actualiza/borra al instante.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from urllib.parse import urlencode

from ..config import GOOGLE_SERVICE_ACCOUNT_JSON, TIMEZONE
from ..models import Appointment, User

log = logging.getLogger("gcal")
_service = None


def api_enabled() -> bool:
    return bool(GOOGLE_SERVICE_ACCOUNT_JSON)


def service_account_email() -> str:
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        return ""
    try:
        return json.loads(GOOGLE_SERVICE_ACCOUNT_JSON).get("client_email", "")
    except ValueError:
        return ""


def _get_service():
    global _service
    if _service is None:
        from google.oauth2 import service_account  # import perezoso: dependencia opcional
        from googleapiclient.discovery import build

        info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/calendar.events"]
        )
        _service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return _service


def _title(a: Appointment) -> str:
    extra = f" + {a.external.full_name}" if a.external else ""
    return f"{a.type} · {a.patient.full_name}{extra}"


def _description(a: Appointment) -> str:
    lines = [f"Paciente: {a.patient.full_name}", f"Tel: {a.patient.phone}", f"Doctor(a): {a.doctor.full_name}"]
    if a.external:
        lines.append(f"Especialista: {a.external.full_name} ({a.external.specialty})")
    if a.notes:
        lines.append(f"Notas: {a.notes}")
    return "\n".join(lines)


def event_body(a: Appointment) -> dict:
    tz = str(TIMEZONE)
    return {
        "summary": _title(a),
        "description": _description(a),
        "start": {"dateTime": a.start.isoformat(), "timeZone": tz},
        "end": {"dateTime": a.end.isoformat(), "timeZone": tz},
        "colorId": "3" if a.external else None,
    }


def sync(a: Appointment, user: User) -> str | None:
    """Crea/actualiza/borra el evento. Devuelve el event_id o None. Nunca lanza excepción."""
    if not api_enabled() or not user.gcal_calendar_id:
        return None
    try:
        svc = _get_service()
        cal = user.gcal_calendar_id
        if a.status == "cancelada":
            if a.gcal_event_id:
                svc.events().delete(calendarId=cal, eventId=a.gcal_event_id).execute()
            return ""
        body = {k: v for k, v in event_body(a).items() if v is not None}
        if a.gcal_event_id:
            ev = svc.events().update(calendarId=cal, eventId=a.gcal_event_id, body=body).execute()
        else:
            ev = svc.events().insert(calendarId=cal, body=body).execute()
        return ev.get("id")
    except Exception as exc:  # la cita se guarda aunque Google falle
        log.warning("No se pudo sincronizar con Google Calendar: %s", exc)
        return None


def add_link(a: Appointment) -> str:
    fmt = "%Y%m%dT%H%M%S"
    params = {
        "action": "TEMPLATE",
        "text": _title(a),
        "dates": f"{a.start.strftime(fmt)}/{a.end.strftime(fmt)}",
        "details": _description(a),
        "ctz": str(TIMEZONE),
    }
    return "https://calendar.google.com/calendar/render?" + urlencode(params)


def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics_feed(user: User, appointments: list[Appointment]) -> str:
    fmt = "%Y%m%dT%H%M%S"
    stamp = datetime.utcnow().strftime(fmt) + "Z"
    tz = str(TIMEZONE)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Consultorio Dental JM//CRM//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Consultorio JM · {user.short_name}",
        f"X-WR-TIMEZONE:{tz}",
    ]
    for a in appointments:
        status = "CANCELLED" if a.status == "cancelada" else "CONFIRMED"
        lines += [
            "BEGIN:VEVENT",
            f"UID:cita-{a.id}@consultorio-jm",
            f"DTSTAMP:{stamp}",
            f"DTSTART;TZID={tz}:{a.start.strftime(fmt)}",
            f"DTEND;TZID={tz}:{a.end.strftime(fmt)}",
            f"SUMMARY:{_ics_escape(_title(a))}",
            f"DESCRIPTION:{_ics_escape(_description(a))}",
            f"STATUS:{status}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
