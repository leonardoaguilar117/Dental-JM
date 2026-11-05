"""Utilidades: fechas locales, contraseñas, formato y enlaces de WhatsApp."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
from datetime import date, datetime
from urllib.parse import quote

from .config import COUNTRY_CODE, TIMEZONE

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def now_local() -> datetime:
    return datetime.now(TIMEZONE).replace(tzinfo=None, microsecond=0)


def today_local() -> date:
    return now_local().date()


# --- contraseñas (PBKDF2, sin dependencias externas) ---
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"pbkdf2${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 200_000)
    return hmac.compare_digest(digest.hex(), digest_hex)


# --- formato ---
def money(value) -> str:
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        v = 0
    return f"-${abs(v):,.2f}" if v < 0 else f"${v:,.2f}"


def money0(value) -> str:
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        v = 0
    return f"-${abs(v):,.0f}" if v < 0 else f"${v:,.0f}"


def fecha(value, fmt: str = "corta") -> str:
    if not value:
        return "—"
    if isinstance(value, datetime):
        d = value
    else:
        d = datetime.combine(value, datetime.min.time())
    if fmt == "larga":
        return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"
    if fmt == "hora":
        return d.strftime("%H:%M")
    if fmt == "fechahora":
        return f"{d.day} {MESES_CORTOS[d.month - 1]} {d.year}, {d:%H:%M}"
    if fmt == "diames":
        return f"{DIAS[d.weekday()][:3]} {d.day} {MESES_CORTOS[d.month - 1]}"
    return f"{d.day} {MESES_CORTOS[d.month - 1]} {d.year}"


def relative_days(d: date | None) -> str:
    if not d:
        return ""
    delta = (d - today_local()).days
    if delta == 0:
        return "hoy"
    if delta == 1:
        return "mañana"
    if delta == -1:
        return "ayer"
    if delta > 0:
        return f"en {delta} días"
    return f"hace {-delta} días"


def digits(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def whatsapp_link(phone: str, message: str) -> str:
    num = digits(phone)
    if len(num) == 10:
        num = COUNTRY_CODE + num
    return f"https://wa.me/{num}?text={quote(message)}"


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value[:16])
    except ValueError:
        return None


def to_float(value, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "").replace("$", "") or default)
    except (TypeError, ValueError):
        return default


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + (month == 12), (month % 12) + 1, 1)
    return start, end


def add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1
