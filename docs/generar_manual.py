"""Genera docs/Manual_Consultorio_Dental_JM.pdf (requiere: pip install reportlab)."""
import os

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "capturas")
OUT = os.path.join(HERE, "Manual_Consultorio_Dental_JM.pdf")

# Fuentes (Segoe UI en Windows; si no existe, Helvetica)
F, FB = "Helvetica", "Helvetica-Bold"
for reg, bold in [("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
                  ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")]:
    if os.path.exists(reg) and os.path.exists(bold):
        pdfmetrics.registerFont(TTFont("UI", reg))
        pdfmetrics.registerFont(TTFont("UIB", bold))
        F, FB = "UI", "UIB"
        break

BRAND = colors.HexColor("#2f6d75")
DARK = colors.HexColor("#1c2030")
INK = colors.HexColor("#1c2030")
MUTED = colors.HexColor("#575d72")
SOFT = colors.HexColor("#f1fbd9")
LINE = colors.HexColor("#d6d9e0")
VIOLET = colors.HexColor("#737a90")
ORANGE = colors.HexColor("#6c4813")
BLUE = colors.HexColor("#0ea1d2")

st = {
    "h1": ParagraphStyle("h1", fontName=FB, fontSize=19, leading=24, textColor=INK, spaceBefore=4, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName=FB, fontSize=13.5, leading=18, textColor=BRAND, spaceBefore=12, spaceAfter=6),
    "h3": ParagraphStyle("h3", fontName=FB, fontSize=11, leading=15, textColor=INK, spaceBefore=8, spaceAfter=3),
    "p": ParagraphStyle("p", fontName=F, fontSize=9.8, leading=14.5, textColor=INK, spaceAfter=6),
    "small": ParagraphStyle("small", fontName=F, fontSize=8.5, leading=12, textColor=MUTED, spaceAfter=4),
    "cap": ParagraphStyle("cap", fontName=F, fontSize=8.3, leading=11, textColor=MUTED, alignment=TA_CENTER, spaceAfter=10),
    "bul": ParagraphStyle("bul", fontName=F, fontSize=9.8, leading=14, textColor=INK, leftIndent=14, bulletIndent=3, spaceAfter=2),
    "code": ParagraphStyle("code", fontName="Courier", fontSize=8.6, leading=12, textColor=INK, backColor=colors.HexColor("#f2f5f4"),
                           borderPadding=6, leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=8),
    "cell": ParagraphStyle("cell", fontName=F, fontSize=8.8, leading=12, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName=FB, fontSize=8.8, leading=12, textColor=INK),
}


def P(t, s="p"):
    return Paragraph(t, st[s])


def bullets(items):
    return [Paragraph(i, st["bul"], bulletText="•") for i in items]


def table(rows, widths, header=True):
    data = [[P(c, "cellb" if (header and r == 0) else "cell") for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), SOFT)]
    t.setStyle(TableStyle(style))
    return t


def shot(name, caption, width=16.5 * cm):
    path = os.path.join(SHOTS, name)
    if not os.path.exists(path):
        return []
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(path).getSize()
    h = width * ih / iw
    max_h = 19 * cm
    if h > max_h:
        width, h = width * max_h / h, max_h
    img = Image(path, width=width, height=h)
    frame = Table([[img]], colWidths=[width + 4])
    frame.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, LINE), ("LEFTPADDING", (0, 0), (-1, -1), 2),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 2),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return [KeepTogether([frame, Spacer(1, 4), P(caption, "cap")])]


# ---------- diagramas ----------
def _arrow(d, x1, y1, x2, y2, color=MUTED):
    d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1.3))
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    s = 6
    d.add(Polygon([x2, y2, x2 - s * math.cos(a - 0.4), y2 - s * math.sin(a - 0.4),
                   x2 - s * math.cos(a + 0.4), y2 - s * math.sin(a + 0.4)], fillColor=color, strokeColor=color))


def _box(d, x, y, w, h, title, sub="", fill=SOFT, stroke=BRAND, tcolor=INK):
    d.add(Rect(x, y, w, h, rx=7, ry=7, fillColor=fill, strokeColor=stroke, strokeWidth=1))
    d.add(String(x + w / 2, y + h - 15, title, fontName=FB, fontSize=8.6, fillColor=tcolor, textAnchor="middle"))
    for i, line in enumerate(sub.split("\n") if sub else []):
        d.add(String(x + w / 2, y + h - 27 - i * 10, line, fontName=F, fontSize=7.2, fillColor=MUTED, textAnchor="middle"))


def flow_snake(steps, cols=4, bw=105, bh=52, gx=26, gy=30, title_colors=None):
    """Diagrama de pasos en zigzag (izq->der, luego der->izq)."""
    rows = (len(steps) + cols - 1) // cols
    W = cols * bw + (cols - 1) * gx + 10
    H = rows * bh + (rows - 1) * gy + 10
    d = Drawing(W, H)
    pos = []
    for i, (t, s) in enumerate(steps):
        r, c = divmod(i, cols)
        if r % 2 == 1:
            c = cols - 1 - c
        x = 5 + c * (bw + gx)
        y = H - 5 - (r + 1) * bh - r * gy
        fill = (title_colors or {}).get(i, SOFT)
        _box(d, x, y, bw, bh, f"{i + 1}. {t}", s, fill=fill)
        pos.append((x, y, r))
    for i in range(len(pos) - 1):
        x, y, r = pos[i]
        nx, ny, nr = pos[i + 1]
        if nr == r:
            if nx > x:
                _arrow(d, x + bw, y + bh / 2, nx, ny + bh / 2)
            else:
                _arrow(d, x, y + bh / 2, nx + bw, ny + bh / 2)
        else:
            _arrow(d, x + bw / 2, y, nx + bw / 2, ny + bh)
    return d


def architecture():
    d = Drawing(480, 255)
    _box(d, 10, 180, 130, 55, "Navegador", "Dra. Jimena / Dr. Juan Carlos\nPC, tableta o celular")
    _box(d, 175, 120, 140, 128, "Contenedor Docker", "", fill=colors.white)
    _box(d, 187, 182, 116, 40, "FastAPI + Uvicorn", "Rutas / sesiones")
    _box(d, 187, 132, 116, 40, "Jinja2 + SQLAlchemy", "Vistas / modelo")
    _box(d, 350, 180, 120, 55, "PostgreSQL (Render)", "o SQLite en demo", fill=colors.HexColor("#e7eefe"), stroke=BLUE)
    _box(d, 350, 95, 120, 55, "Google Calendar", "Feed iCal / API", fill=colors.HexColor("#f0e9fe"), stroke=VIOLET)
    _box(d, 10, 95, 130, 55, "WhatsApp (wa.me)", "Mensaje redactado\nenvío manual", fill=colors.HexColor("#e6f6eb"), stroke=colors.HexColor("#16a34a"))
    _box(d, 175, 15, 140, 60, "Render.com", "Build del Dockerfile\nHTTPS + dominio .onrender.com", fill=colors.HexColor("#fdf3e2"), stroke=ORANGE)
    _arrow(d, 140, 207, 187, 202)
    _arrow(d, 303, 202, 350, 207)
    _arrow(d, 303, 150, 350, 125)
    _arrow(d, 187, 150, 140, 125)
    _arrow(d, 245, 75, 245, 120)
    return d


def on_page(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFillColor(BRAND)
        canvas.rect(0, letter[1] - 6, letter[0], 6, fill=1, stroke=0)
        canvas.setFont(F, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(2 * cm, 1.2 * cm, "Consultorio Dental JM · Manual de funcionamiento (demo ilustrativo)")
        canvas.drawRightString(letter[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.restoreState()


def cover(canvas, doc):
    canvas.saveState()
    w, h = letter
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#2a3046"))
    canvas.circle(w - 60, h - 80, 210, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#e2f8af"))
    canvas.roundRect(2.2 * cm, h - 6 * cm, 1.6 * cm, 1.6 * cm, 8, fill=1, stroke=0)
    canvas.setFillColor(DARK)
    canvas.setFont(FB, 17)
    canvas.drawCentredString(3.0 * cm, h - 5.45 * cm, "JM")
    canvas.setFillColor(colors.white)
    canvas.setFont(FB, 30)
    canvas.drawString(2.2 * cm, h - 9.5 * cm, "Consultorio Dental JM")
    canvas.setFont(F, 16)
    canvas.setFillColor(colors.HexColor("#a6c7bf"))
    canvas.drawString(2.2 * cm, h - 10.7 * cm, "Manual de funcionamiento y flujo de trabajo")
    canvas.setFont(F, 11)
    lines = ["Sistema de gestión: pacientes, historia clínica, agenda, cobros,",
             "gastos compartidos, recordatorios e inventario del depósito dental.",
             "", "FastAPI · Docker · Render"]
    for i, l in enumerate(lines):
        canvas.drawString(2.2 * cm, h - 12.5 * cm - i * 16, l)
    canvas.setFillColor(colors.white)
    canvas.setFont(FB, 11)
    canvas.drawString(2.2 * cm, 4.2 * cm, "Dra. Jimena Juárez Aguilar · Ortodoncia")
    canvas.drawString(2.2 * cm, 3.5 * cm, "Dr. Juan Carlos Montaño López · Estética dental")
    canvas.setFont(F, 9)
    canvas.setFillColor(colors.HexColor("#7aa59b"))
    canvas.drawString(2.2 * cm, 2.4 * cm, "Versión 1.0 demo · noviembre 2026 · datos ficticios")
    canvas.restoreState()


def build():
    s = []
    s.append(PageBreak())  # portada dibujada por cover()

    # 1. Introducción
    s.append(P("1. ¿Qué es este sistema?", "h1"))
    s.append(P("Es una aplicación web para el consultorio de la <b>Dra. Jimena Juárez Aguilar</b> (ortodoncista) y el "
               "<b>Dr. Juan Carlos Montaño López</b> (estética dental), que atienden a sus pacientes y además administran el "
               "consultorio. Reúne en un solo lugar lo que hoy se lleva en libretas, chats y hojas de cálculo:"))
    s += bullets([
        "<b>Pacientes e historia clínica</b> con odontograma interactivo y notas de evolución (estructura basada en la NOM-004).",
        "<b>Agenda compartida</b> que también considera al <b>cirujano maxilofacial externo</b> (sin usuario) y evita empalmes.",
        "<b>Tratamientos, presupuestos y abonos</b>: lo cobrado y lo restante por paciente.",
        "<b>Gastos propios y compartidos</b> (renta, luz, agua, internet…) con reparto configurable y ajuste entre doctores.",
        "<b>Dashboard</b> de ingresos, egresos, utilidad y cuentas por cobrar, por doctor o del consultorio.",
        "<b>Avisos y recordatorios</b> para contactar manualmente a los pacientes por WhatsApp (limpiezas, ajustes, seguimientos).",
        "<b>Google Calendar</b>: feed iCal, botón «Añadir a Google» y sincronización por API (opcional).",
        "<b>Inventario del depósito dental</b>, exclusivo de la Dra. Jimena: lotes, caducidades, stock mínimo, ventas y kardex.",
    ])
    s.append(P("Se trata de un <b>demo ilustrativo</b>: incluye datos ficticios (16 pacientes, seis meses de cobros y gastos, "
               "citas, recordatorios y 22 productos de inventario) para que el flujo se pueda recorrer de punta a punta.", "small"))

    s.append(P("1.1 Usuarios y permisos", "h2"))
    s.append(table([
        ["Usuario", "Especialidad", "Acceso", "Credenciales demo"],
        ["Dra. Jimena Juárez Aguilar", "Ortodoncia", "Todo + <b>Inventario</b> del depósito", "jimena / demo123"],
        ["Dr. Juan Carlos Montaño López", "Estética dental", "Todo excepto inventario", "carlos / demo123"],
        ["Dr. Ricardo Salinas Vega (ficticio)", "Cirujano maxilofacial", "<b>Sin usuario.</b> Se asigna a citas y tratamientos; se le avisa por WhatsApp", "—"],
    ], [4.6 * cm, 3 * cm, 5.6 * cm, 3.3 * cm]))
    s.append(P("Ambos doctores ven a todos los pacientes y la agenda completa, porque comparten el consultorio. Las cifras del "
               "dashboard y de finanzas muestran por defecto <b>«Mis números»</b> y se pueden cambiar a <b>«Consultorio»</b>.", "small"))

    # 2. Arquitectura
    s.append(P("1.2 Arquitectura", "h2"))
    s.append(architecture())
    s.append(Spacer(1, 6))
    s.append(table([
        ["Capa", "Tecnología", "Detalle"],
        ["Backend", "FastAPI 0.115 + Uvicorn", "Rutas HTML y JSON, sesiones firmadas, documentación OpenAPI en /api/docs"],
        ["Datos", "SQLAlchemy 2 · PostgreSQL / SQLite", "13 tablas: usuarios, especialistas, pacientes, historias, notas, citas, tratamientos, pagos, gastos, recordatorios, productos, lotes y movimientos"],
        ["Interfaz", "Jinja2 + CSS propio", "Responsiva; Chart.js (gráficas) y FullCalendar (agenda) desde CDN"],
        ["Despliegue", "Docker → Render", "Dockerfile + render.yaml (Blueprint con base de datos PostgreSQL)"],
    ], [2.6 * cm, 5 * cm, 8.9 * cm]))
    s.append(P("1.3 Diseño visual", "h2"))
    s.append(P("La interfaz usa un <b>marco lima</b> (menú y barra superior) que rodea una <b>hoja blanca</b> donde está el trabajo. "
               "El color se reserva para lo que significa algo:"))
    s.append(table([
        ["Color", "Uso"],
        ["<font color='#4f6a12'>■</font> #E2F8AF lima", "Marco de la app, botón de WhatsApp, selección y resaltado al pasar el cursor"],
        ["<font color='#0ea1d2'>■</font> #0EA1D2 cerúleo", "El dato principal: ingresos, hora actual, resinas en el odontograma"],
        ["<font color='#418d96'>■</font> #418D96 teal", "Dra. Jimena (agenda, avatares, carriles) y brackets"],
        ["<font color='#6c4813'>■</font> #6C4813 café", "Dr. Juan Carlos y endodoncias"],
        ["<font color='#737a90'>■</font> #737A90 pizarra", "Cirujano maxilofacial, egresos y textos secundarios"],
    ], [4.6 * cm, 11.9 * cm]))
    s.append(P("<b>Cuatro temas</b> se eligen con el botón de paleta del encabezado (se recuerda por navegador): <b>Lima</b> (claro), "
               "<b>Arrecife</b> (oscuro: #1C4A6D, #07A2C8, #6CF7A0, #A95482, #2F7B83), <b>Lavanda</b> (claro: #012880, #85B559, #A393BE, #C0CDE6, #63756D) "
               "y <b>Grafito</b> (oscuro neutro con acentos lavanda y verde). El cambio de tema se hace con un fundido cruzado de toda la página."))
    s.append(P("<b>3D con Three.js:</b> el tablero muestra un molar anatómico (cuatro cúspides con surcos y tres raíces); el expediente genera un "
               "<b>tipodonto 3D</b> a partir del odontograma (32 piezas por tipo, encías y brackets con alambre). El botón <b>Cerrada / Abierta</b> "
               "abre la boca para ver las caras oclusales, donde se marcan caries y resinas; al elegir una pieza en la lista, la boca se abre y la "
               "cámara la muestra de cerca. Se gira arrastrando y al pasar el cursor cada pieza muestra su diagnóstico."))
    s.append(P("Los botones funcionan como teclas: el principal es oscuro con un labio lima que se hunde al presionarlo, y los secundarios "
               "se llenan de lima de izquierda a derecha al pasar el cursor. Las pestañas tienen un subrayado que se desliza, los avisos "
               "aparecen como notificaciones temporales y, en navegadores compatibles, la página cambia de pantalla con una transición suave. "
               "Quien activa «reducir movimiento» en su sistema ve todo sin animaciones.", "small"))
    s.append(PageBreak())

    # 3. Flujo de trabajo
    s.append(P("2. Flujo de trabajo", "h1"))
    s.append(P("2.1 Ciclo de atención de un paciente", "h2"))
    s.append(P("Este es el recorrido completo de un paciente, desde que llega hasta que se le vuelve a contactar:"))
    s.append(flow_snake([
        ("Registro", "Ficha de identificación\ny doctor tratante"),
        ("Historia clínica", "Antecedentes, alergias,\nexploración, odontograma"),
        ("Presupuesto", "Tratamiento, costo,\nsesiones, maxilofacial"),
        ("Agendar cita", "Calendario; valida\nempalmes doctor/externo"),
        ("Confirmar", "WhatsApp del día\nanterior (Avisos)"),
        ("Atención", "Marcar atendida + nota\nde evolución + sesión"),
        ("Cobro / abono", "Recibo; el saldo se\nactualiza solo"),
        ("Recordatorio", "Automático por tipo de\ncita (6 meses, 4 sem…)"),
    ], cols=4))
    s.append(Spacer(1, 6))
    s.append(table([
        ["Paso", "Dónde", "Qué hace el sistema"],
        ["1. Registro", "Pacientes → Nuevo", "Crea el expediente con un folio y una historia clínica vacía."],
        ["2. Historia clínica", "Expediente → Historia clínica", "Guarda el interrogatorio y la exploración; el odontograma se marca con clics. Las alergias y enfermedades se muestran como alertas rojas en todo el sistema."],
        ["3. Presupuesto", "Expediente → Tratamientos y pagos", "Registra costo, descuento y sesiones. Si participa el maxilofacial, sus honorarios se cargan como gasto del doctor. Presupuesto imprimible."],
        ["4. Cita", "Agenda (clic en un horario)", "Sugiere la duración según el tipo; en cirugía preselecciona al maxilofacial. Bloquea empalmes."],
        ["5. Confirmación", "Avisos", "Lista las citas de mañana con un botón de WhatsApp y el mensaje redactado."],
        ["6. Atención", "Detalle de la cita", "Al marcarla como atendida: guarda la nota de evolución, suma una sesión al tratamiento y crea el siguiente recordatorio."],
        ["7. Cobro", "Expediente → Tratamientos", "Registra el abono (efectivo, tarjeta, transferencia), impide pagar de más y genera un recibo."],
        ["8. Recordatorio", "Avisos / Recordatorios", "Aparece 7 días antes. El doctor abre WhatsApp, revisa el mensaje y lo envía; luego lo marca como completado."],
    ], [3 * cm, 4.2 * cm, 9.3 * cm]))

    s.append(P("2.2 Rutina diaria sugerida", "h2"))
    s.append(flow_snake([
        ("Inicio (dashboard)", "Citas de hoy, avisos,\nalertas de inventario"),
        ("Avisos", "Enviar recordatorios y\nconfirmar las de mañana"),
        ("Consultas", "Atender y marcar cada\ncita como atendida"),
        ("Cierre del día", "Registrar abonos y\ngastos del día"),
    ], cols=4))
    s.append(PageBreak())

    s.append(P("2.3 Flujo financiero mensual", "h2"))
    s.append(flow_snake([
        ("Copiar recurrentes", "Renta, luz, internet\ndel mes anterior"),
        ("Registrar gastos", "Propio o compartido;\nquién lo pagó"),
        ("Revisar dashboard", "Ingresos, egresos,\nutilidad vs. mes previo"),
        ("Ajuste entre doctores", "Quién pagó de más\nen los compartidos"),
        ("Cuentas por cobrar", "Saldos con 30+ días;\nrecordar por WhatsApp"),
        ("Exportar CSV", "Cobros y gastos\npara el contador"),
    ], cols=3, bw=135))
    s.append(Spacer(1, 6))
    s.append(P("<b>Cómo se calculan los números:</b>"))
    s += bullets([
        "<b>Ingresos de un doctor</b> = abonos de sus tratamientos + ventas de mostrador del depósito (solo la Dra. Jimena).",
        "<b>Egresos de un doctor</b> = sus gastos propios + su porcentaje de los gastos compartidos (50/50 por defecto, ajustable en Configuración).",
        "<b>Ajuste entre doctores</b>: compara lo que cada uno <i>pagó</i> de los compartidos con lo que le <i>correspondía</i>. Una diferencia positiva indica que el otro doctor le debe esa cantidad.",
        "<b>Por cobrar</b> = suma de los saldos de los tratamientos en proceso y terminados.",
    ])

    s.append(P("2.4 Flujo del inventario (solo Dra. Jimena)", "h2"))
    s.append(flow_snake([
        ("Alta de producto", "SKU, categoría, mínimo,\ncosto, precio, caduca?"),
        ("Entrada por lote", "Cantidad, lote y fecha\nde caducidad"),
        ("Salida FEFO", "Uso, venta o merma;\nsale lo que caduca antes"),
        ("Alertas", "Por caducar (60 d),\ncaducados, stock bajo"),
        ("Acción", "Usar primero, dar de\nbaja o reordenar"),
        ("Kardex / conteo", "Historial y ajuste\npor conteo físico"),
    ], cols=3, bw=135))
    s.append(P("Semáforo de caducidad: <font color='#15803d'><b>verde</b></font> más de 60 días · "
               "<font color='#b45309'><b>ámbar</b></font> 60 días o menos · <font color='#c2292e'><b>rojo</b></font> menos de 30 días o caducado. "
               "Los lotes caducados no se pueden vender ni usar; solo dar de baja como merma.", "small"))
    s.append(PageBreak())

    # 4. Módulos con capturas
    s.append(P("3. Recorrido por los módulos", "h1"))
    s.append(P("3.1 Inicio de sesión", "h2"))
    s.append(P("Cada doctor elige su tarjeta e ingresa su contraseña. La Dra. Jimena ve además el acceso al depósito dental."))
    s += shot("01_login.png", "Pantalla de acceso", 14 * cm)
    s.append(P("3.2 Dashboard", "h2"))
    s.append(P("Muestra los indicadores del mes (con variación contra el mes anterior), la gráfica de los últimos 6 meses, los gastos por "
               "categoría, las cuentas por cobrar, el avance de los tratamientos, las citas de hoy, los avisos y las alertas de inventario. "
               "El selector superior cambia entre <b>Mis números</b> y <b>Consultorio</b>, y permite navegar por los meses."))
    s.append(P("Debajo de los indicadores está la <b>Jornada de hoy</b>: un carril por doctor y otro para el maxilofacial, con "
               "cada cita en su horario y una línea azul que marca la hora actual. Se ve de un vistazo quién está ocupado y cuándo."))
    s += shot("03_dashboard_consultorio.png", "Dashboard en vista «Consultorio», con la Jornada de hoy")
    s.append(P("3.3 Agenda", "h2"))
    s.append(P("Calendario semanal, diario, mensual o en lista. Cada doctor tiene su color (teal la Dra. Jimena, café el Dr. Juan Carlos) y las citas con el maxilofacial van en "
               "gris pizarra. Con un clic en un horario libre se abre el formulario de nueva cita. Las citas canceladas aparecen tachadas."))
    s += shot("04_agenda.png", "Agenda compartida con filtro por doctor y especialista externo")
    s.append(P("3.4 Pacientes y expediente", "h2"))
    s.append(P("La lista permite buscar y filtrar por doctor o por saldo pendiente, y muestra las alertas médicas. El expediente tiene "
               "pestañas de Resumen, Historia clínica, Evolución, Tratamientos y pagos, Citas y Recordatorios."))
    s += shot("05_pacientes.png", "Lista de pacientes")
    s += shot("06_paciente_resumen.png", "Tipodonto 3D generado desde el odontograma, con las piezas afectadas por zona")
    s += shot("22_tipodonto_abierto.png", "Tipodonto con la boca abierta: caras oclusales con resina (16) y piezas por extraer")
    s += shot("07_historia_clinica.png", "Historia clínica con odontograma interactivo (numeración FDI)", 13 * cm)
    s += shot("08_tratamientos.png", "Tratamientos, abonos y saldo; presupuesto con especialista externo")
    s.append(P("3.5 Citas con el cirujano maxilofacial", "h2"))
    s.append(P("El especialista no tiene usuario, pero se elige en la cita. El sistema impide asignarlo a dos citas que se traslapen "
               "(aunque sean de doctores distintos) y ofrece un botón para avisarle por WhatsApp con los datos de la cirugía. "
               "Al marcar la cita como atendida se crea el recordatorio de revisión post-quirúrgica."))
    s += shot("09_cita_maxilofacial.png", "Detalle de una cita de cirugía con el maxilofacial")
    s.append(P("3.6 Finanzas", "h2"))
    s.append(P("Tiene tres pestañas: <b>Cobros del mes</b>, <b>Cuentas por cobrar</b> y <b>Gastos</b>. El formulario de gastos pregunta si el gasto "
               "es propio o compartido y quién lo pagó. Incluye el botón «Copiar recurrentes» y exportación a CSV."))
    s += shot("10_finanzas_gastos.png", "Gastos con reparto y ajuste entre doctores")
    s.append(P("3.7 Avisos y recordatorios", "h2"))
    s.append(P("El centro de avisos reúne cuatro listas: recordatorios a pacientes, confirmaciones de las citas de mañana, saldos atrasados y "
               "alertas de inventario. El botón de WhatsApp abre el chat con el mensaje listo; <b>el doctor decide si lo envía</b>. "
               "Al hacerlo, el recordatorio pasa a «enviado»."))
    s += shot("11_avisos.png", "Centro de avisos")
    s += shot("12_recordatorios.png", "Gestión de recordatorios: pendientes, enviados y completados")
    s.append(P("3.8 Inventario del depósito dental", "h2"))
    s.append(P("Indicadores de valor, stock bajo, productos por caducar y caducados; tabla de próximas caducidades con acciones; catálogo con "
               "filtros. En cada producto se registran entradas por lote, salidas (uso, venta o merma) y ajustes por conteo físico."))
    s += shot("13_inventario.png", "Inventario con alertas de caducidad")
    s += shot("14_producto.png", "Detalle de producto: lotes FEFO, entrada, salida y kardex")
    s.append(P("3.9 Configuración", "h2"))
    s += shot("15_configuracion.png", "Perfil, Google Calendar, reparto de gastos y especialistas externos")
    s.append(P("3.10 Temas", "h2"))
    s += shot("20_tema_arrecife.png", "Tema Arrecife (oscuro)")
    s += shot("20_tema_lavanda.png", "Tema Lavanda (claro)")
    s += shot("21_tipodonto_grafito.png", "Tema Grafito con el expediente")
    s.append(P("3.11 Uso en celular", "h2"))
    s += shot("17_movil_dashboard.png", "Vista móvil (menú lateral desplegable)", 6 * cm)
    s.append(PageBreak())

    # 5. Google Calendar
    s.append(P("4. Integración con Google Calendar", "h1"))
    s.append(P("<b>Sí es posible.</b> El sistema ofrece tres niveles, de menor a mayor configuración. Se pueden usar al mismo tiempo."))
    s.append(table([
        ["Opción", "Cómo se activa", "Ventajas", "Limitaciones"],
        ["1. Suscripción iCal (recomendada)", "Configuración → copiar el enlace privado → en Google Calendar: <i>Otros calendarios → + → Desde URL</i>",
         "Sin costo ni credenciales; las citas aparecen en el celular de cada doctor", "Un solo sentido; Google refresca cada 8–24 h"],
        ["2. Botón «Añadir a Google»", "Ya disponible en cada cita", "Inmediato, un clic", "Manual, cita por cita"],
        ["3. API (cuenta de servicio)", "Variable GOOGLE_SERVICE_ACCOUNT_JSON + compartir el calendario + pegar su ID en Configuración",
         "Tiempo real: crea, mueve y borra eventos al guardar", "Requiere un proyecto en Google Cloud (gratuito)"],
    ], [3.4 * cm, 5 * cm, 4.2 * cm, 3.9 * cm]))
    s.append(P("Pasos para la opción 3 (API)", "h3"))
    s += bullets([
        "En <b>console.cloud.google.com</b>, crear un proyecto y habilitar <b>Google Calendar API</b>.",
        "En <i>IAM → Cuentas de servicio</i>, crear una cuenta y descargar su llave JSON.",
        "En Render → Environment, crear <b>GOOGLE_SERVICE_ACCOUNT_JSON</b> y pegar el contenido completo del JSON.",
        "Cada doctor, en Google Calendar: <i>Configuración del calendario → Compartir con personas</i>, agrega el correo de la cuenta de servicio "
        "(lo muestra la app) con permiso <b>«Hacer cambios en eventos»</b>.",
        "Copiar el <b>ID del calendario</b> (sección «Integrar el calendario») y pegarlo en Configuración → Mi perfil.",
        "Desde ese momento, cada cita creada, reprogramada o cancelada se refleja en Google al instante. Si Google falla, la cita se guarda de todos modos.",
    ])
    s.append(P("Una sincronización en ambos sentidos (que lo creado en Google aparezca en la app) requiere OAuth por usuario y webhooks; "
               "se propone para una versión posterior.", "small"))

    # 6. Despliegue
    s.append(P("5. Despliegue en Render con Docker", "h1"))
    s.append(P("Estructura del proyecto", "h3"))
    s.append(P("app/ main.py · config.py · database.py · models.py · seed.py · web.py<br/>"
               "app/routers/ auth · dashboard · patients · appointments · finance · reminders · inventory · settings<br/>"
               "app/services/ finance · inventory · notifications · gcal<br/>"
               "app/templates/ (HTML Jinja2) · app/static/ (CSS, JS)<br/>"
               "Dockerfile · render.yaml · requirements.txt · .env.example · docs/", "code"))
    s.append(P("Opción A: Blueprint (recomendada)", "h3"))
    s += bullets([
        "Subir la carpeta del proyecto a un repositorio de GitHub o GitLab.",
        "En <b>dashboard.render.com</b>: <i>New → Blueprint</i> y seleccionar el repositorio. Render lee <b>render.yaml</b> y crea el servicio "
        "web (Docker) y la base de datos PostgreSQL, conectándolos mediante DATABASE_URL.",
        "Esperar el build (unos 3–5 min). La app queda en <b>https://consultorio-dental-jm.onrender.com</b> (o el nombre disponible).",
        "Entrar con <b>jimena / demo123</b> y cambiar las contraseñas en Configuración.",
    ])
    s.append(P("Opción B: servicio web manual", "h3"))
    s += bullets([
        "<i>New → Web Service</i> → repositorio → <b>Runtime: Docker</b>. Render detecta el Dockerfile.",
        "Variables: <b>SECRET_KEY</b> (aleatoria), <b>SEED_DEMO</b>=true, y opcionalmente <b>DATABASE_URL</b> de una base PostgreSQL de Render.",
        "Health check path: <b>/healthz</b>.",
    ])
    s.append(P("Probar localmente con Docker", "h3"))
    s.append(P("docker build -t consultorio-jm .<br/>docker run -p 8000:8000 -e SECRET_KEY=algo-secreto consultorio-jm<br/># abrir http://localhost:8000", "code"))
    s.append(P("Variables de entorno", "h3"))
    s.append(table([
        ["Variable", "Uso", "Valor por defecto"],
        ["SECRET_KEY", "Firma de las cookies de sesión", "(cambiar obligatoriamente)"],
        ["DATABASE_URL", "PostgreSQL de Render; si está vacía, usa SQLite", "SQLite ./data"],
        ["SEED_DEMO", "Carga los datos ficticios si la base está vacía", "true"],
        ["TZ_CONSULTORIO", "Zona horaria", "America/Mexico_City"],
        ["WHATSAPP_COUNTRY_CODE", "Lada para los enlaces wa.me", "52"],
        ["EXPIRY_ALERT_DAYS / REMINDER_WINDOW_DAYS", "Días de anticipación de las alertas", "60 / 7"],
        ["GOOGLE_SERVICE_ACCOUNT_JSON", "Activa la sincronización por API", "(vacía)"],
    ], [5.4 * cm, 7 * cm, 4.1 * cm]))
    s.append(P("<b>Importante sobre el plan gratuito de Render:</b> el servicio se «duerme» tras 15 minutos sin uso (la primera carga tarda "
               "unos 30–50 s), el disco del contenedor es efímero (por eso en producción se usa PostgreSQL, no SQLite) y la base de datos "
               "gratuita expira a los 30 días. Para uso real se recomienda el plan Starter con PostgreSQL de pago y respaldos.", "small"))
    s.append(PageBreak())

    # 7. Reglas y siguientes pasos
    s.append(P("6. Reglas de negocio principales", "h1"))
    s.append(table([
        ["Regla", "Comportamiento"],
        ["Empalmes", "Un doctor o el maxilofacial no pueden tener dos citas activas traslapadas (se puede forzar)."],
        ["Abonos", "No pueden exceder el saldo. El primer abono convierte el presupuesto en «en proceso»."],
        ["Fin de tratamiento", "Cuando las sesiones realizadas alcanzan las planeadas, el tratamiento pasa a «terminado»."],
        ["Honorarios externos", "Se registran como gasto propio del doctor responsable del tratamiento."],
        ["Recordatorios automáticos", "Limpieza: 180 días · Ajuste de ortodoncia: 28 · Blanqueamiento: 180 · Carillas: 90 · Cirugía: 7 · Valoración: 14."],
        ["Mensajes", "Nunca se envían automáticamente: el sistema prepara el texto y el doctor lo manda."],
        ["Inventario", "Salidas FEFO; los lotes caducados solo pueden darse de baja."],
        ["Pacientes", "Se archivan, no se borran (conservación del expediente, NOM-004)."],
    ], [4 * cm, 12.5 * cm]))
    s.append(P("7. Limitaciones del demo y siguientes pasos", "h1"))
    s += bullets([
        "Adjuntar radiografías y fotografías (almacenamiento S3 o Render Disk).",
        "Facturación CFDI 4.0 mediante un PAC (Facturama, FacturAPI).",
        "WhatsApp Business API para envíos automáticos con plantillas aprobadas por Meta.",
        "Sincronización bidireccional con Google Calendar (OAuth + webhooks).",
        "Rol de asistente/recepción, bitácora de auditoría completa y doble factor de autenticación.",
        "Periodontograma, versiones del odontograma y firma digital del consentimiento.",
        "Órdenes de compra a proveedores y lector de código de barras para el depósito.",
    ])
    s.append(P("El documento <b>REQUISITOS_FUNCIONALES.md</b> detalla cada requisito con su prioridad y estado, además de la comparación con la competencia.", "small"))

    doc = SimpleDocTemplate(OUT, pagesize=letter, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                            bottomMargin=1.8 * cm, title="Consultorio Dental JM · Manual", author="Consultorio Dental JM")
    doc.build(s, onFirstPage=cover, onLaterPages=on_page)
    print("PDF generado:", OUT)


if __name__ == "__main__":
    build()
