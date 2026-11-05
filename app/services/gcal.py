"""Integración con Google Calendar.

1. Sin configuración: al agendar, botón "Agregar a Google Calendar" con el evento prellenado.
2. Sincronización automática vía Google Calendar API con una cuenta de servicio:
   - Definir GOOGLE_SERVICE_ACCOUNT_JSON (contenido JSON de la llave).
   - Cada doctor comparte su calendario con el correo de la cuenta de servicio
     ("Hacer cambios en eventos") y pega el ID del calendario en Configuración.
   Al crear/editar/cancelar una cita, el evento se crea/actualiza/borra al instante.
"""
from __future__ import annotations

import json
import logging
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
    return f"{a.type} · {a.patient.full_name}"


def _description(a: Appointment) -> str:
    lines = [f"Paciente: {a.patient.full_name}", f"Tel: {a.patient.phone}", f"Doctor(a): {a.doctor.full_name}"]
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

