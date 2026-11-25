"""Configuración central leída de variables de entorno (compatible con Render)."""
import os
from zoneinfo import ZoneInfo

APP_NAME = "Consultorio Dental JM"
DEFAULT_SECRET = "cambia-esta-clave-en-produccion"
SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET)
# Producción = Render (o ENVIRONMENT=production): cookies solo por HTTPS, sin documentación pública de la API
IS_PRODUCTION = bool(os.getenv("RENDER")) or os.getenv("ENVIRONMENT", "").lower() == "production"
HTTPS_ONLY = os.getenv("HTTPS_ONLY", "true" if IS_PRODUCTION else "false").lower() in ("1", "true", "yes", "si")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "")  # vacío: "demo123" en local, aleatoria en producción

# Datos del establecimiento (NOM-004-SSA3-2012, 5.9 / 10.1.1): aparecen en historia clínica y consentimientos
CLINIC_NAME = os.getenv("CLINIC_NAME", "Consultorio Dental JM")
CLINIC_RAZON_SOCIAL = os.getenv("CLINIC_RAZON_SOCIAL", "")
CLINIC_ADDRESS = os.getenv("CLINIC_ADDRESS", "")
CLINIC_CITY = os.getenv("CLINIC_CITY", "Ciudad de México")
CLINIC_PHONE = os.getenv("CLINIC_PHONE", "")
CLINIC_LICENCIA = os.getenv("CLINIC_LICENCIA", "")  # aviso de funcionamiento / licencia sanitaria COFEPRIS
CLINIC_RESPONSABLE = os.getenv("CLINIC_RESPONSABLE", "")  # responsable sanitario
CLINIC_RESPONSABLE_CEDULA = os.getenv("CLINIC_RESPONSABLE_CEDULA", "")
RETENTION_YEARS = 5  # NOM-004-SSA3-2012, 5.4: conservación mínima del expediente
TIMEZONE = ZoneInfo(os.getenv("TZ_CONSULTORIO", "America/Mexico_City"))
# Datos iniciales cuando la base está vacía:
#   "demo"    → demostración completa (pacientes, citas, tratamientos, finanzas e inventario ficticios)
#   "inicial" → solo las cuentas de los doctores y 4 pacientes de ejemplo (para empezar en producción)
#   "ninguno" → no crea nada
# SEED_DEMO=true/false se respeta por compatibilidad: true → "demo", false → "inicial".
_seed_legacy = os.getenv("SEED_DEMO", "").lower()
SEED = os.getenv("SEED", "").lower() or (
    "demo" if _seed_legacy in ("1", "true", "yes", "si") else "inicial" if _seed_legacy else
    ("inicial" if IS_PRODUCTION else "demo"))
SEED_DEMO = SEED != "ninguno"  # alias antiguo
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
    "extraido": ("Extraído", "#8c2f39"),
    "bracket": ("Bracket", "#418d96"),
}

# Exploración de lengua y encía (historia clínica)
LENGUA_OPCIONES = [
    "Lengua geográfica", "Lengua fisurada", "Lengua saburral", "Glositis", "Macroglosia", "Anquiloglosia",
    "Candidiasis oral", "Úlceras / aftas", "Leucoplasia", "Otro",
]
ENCIA_OPCIONES = [
    "Gingivitis", "Periodontitis", "Recesión gingival", "Hiperplasia gingival", "Sangrado al sondeo",
    "Bolsas periodontales", "Absceso periodontal", "Pericoronitis", "Movilidad dental", "Otro",
]

# Historia clínica (NOM-004-SSA3-2012 y NOM-013-SSA2-2015)
ESTADOS_CIVILES = ["", "Soltero(a)", "Casado(a)", "Unión libre", "Divorciado(a)", "Viudo(a)"]
GRUPOS_SANGUINEOS = ["", "O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-", "Se desconoce"]
# Interrogatorio por aparatos y sistemas
APARATOS = [
    ("cardiovascular", "Cardiovascular"), ("respiratorio", "Respiratorio"), ("digestivo", "Digestivo"),
    ("genitourinario", "Genitourinario"), ("endocrino", "Endocrino"), ("hematologico", "Hematológico / linfático"),
    ("nervioso", "Nervioso"), ("musculoesqueletico", "Musculoesquelético"), ("piel", "Piel y anexos"),
]
NOTE_KINDS = ["Evolución", "Interconsulta", "Referencia / traslado", "Nota aclaratoria"]
CALIDADES_CONSENTIMIENTO = ["Paciente", "Madre / padre", "Tutor", "Representante legal"]
