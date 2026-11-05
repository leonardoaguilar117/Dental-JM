"""Configuración central leída de variables de entorno (compatible con Render)."""
import os
from zoneinfo import ZoneInfo

APP_NAME = "Consultorio Dental JM"
SECRET_KEY = os.getenv("SECRET_KEY", "cambia-esta-clave-en-produccion")
TIMEZONE = ZoneInfo(os.getenv("TZ_CONSULTORIO", "America/Mexico_City"))
SEED_DEMO = os.getenv("SEED_DEMO", "true").lower() in ("1", "true", "yes", "si")
COUNTRY_CODE = os.getenv("WHATSAPP_COUNTRY_CODE", "52")

# Google Calendar (opcional). Si no se configuran, la app usa el feed iCal + enlaces "Añadir a Google".
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

# Días de anticipación para alertas
EXPIRY_ALERT_DAYS = int(os.getenv("EXPIRY_ALERT_DAYS", "60"))
REMINDER_WINDOW_DAYS = int(os.getenv("REMINDER_WINDOW_DAYS", "7"))

# Reglas de recordatorio automático: tipo de cita atendida -> (días para el siguiente aviso, motivo)
REMINDER_RULES = {
    "Limpieza dental": (180, "Limpieza semestral"),
    "Ajuste de ortodoncia": (28, "Ajuste mensual de ortodoncia"),
    "Blanqueamiento": (180, "Revisión / retoque de blanqueamiento"),
    "Carillas / coronas": (90, "Control de carillas"),
    "Extracción / cirugía": (7, "Revisión post-quirúrgica"),
    "Valoración": (14, "Seguimiento de valoración (presupuesto)"),
}

APPOINTMENT_TYPES = [
    "Valoración",
    "Limpieza dental",
    "Ajuste de ortodoncia",
    "Colocación de brackets / alineadores",
    "Retiro de aparatología",
    "Blanqueamiento",
    "Carillas / coronas",
    "Resinas estéticas",
    "Diseño de sonrisa",
    "Extracción / cirugía",
    "Urgencia",
    "Otro",
]

APPOINTMENT_STATUSES = ["programada", "confirmada", "atendida", "cancelada", "no asistió"]
PAYMENT_METHODS = ["Efectivo", "Tarjeta débito", "Tarjeta crédito", "Transferencia"]
EXPENSE_CATEGORIES = [
    "Renta",
    "Luz",
    "Agua",
    "Internet / teléfono",
    "Material dental",
    "Laboratorio",
    "Honorarios especialista",
    "Mantenimiento de equipo",
    "Limpieza / insumos generales",
    "Publicidad",
    "Impuestos / contador",
    "Compra de inventario",
    "Otro",
]
PRODUCT_CATEGORIES = [
    "Ortodoncia",
    "Resinas y adhesivos",
    "Anestésicos",
    "Desechables",
    "Higiene / profilaxis",
    "Blanqueamiento",
    "Impresión y modelos",
    "Instrumental",
    "Esterilización",
    "Otro",
]
PRODUCT_UNITS = ["pieza", "caja", "paquete", "kit", "frasco", "jeringa", "cartucho", "rollo", "bolsa"]

TOOTH_STATES = {
    "sano": ("Sano", "#f3f5f8"),
    "caries": ("Caries", "#c4242a"),
    "obturado": ("Obturado / resina", "#0ea1d2"),
    "endodoncia": ("Endodoncia", "#6c4813"),
    "corona": ("Corona / carilla", "#e2f8af"),
    "ausente": ("Ausente", "#d3d6de"),
    "extraer": ("Por extraer", "#1c2030"),
    "bracket": ("Bracket", "#418d96"),
}
