# Requisitos funcionales: Consultorio Dental JM

**Proyecto:** Sistema de gestión para consultorio dental (demo ilustrativo)
**Usuarios:** Dra. Jimena Juárez Aguilar (Ortodoncia + depósito dental) y Dr. Juan Carlos Montaño López (Estética dental)
**Participante sin usuario:** cirujano maxilofacial externo (extracciones y cirugías)
**Tecnología:** FastAPI + SQLAlchemy + Jinja2 · Docker · Render
**Versión del documento:** 1.0 · noviembre 2026

---

## 1. Contexto y objetivo

Dos odontólogos comparten un consultorio y también lo administran. Hoy no tienen un control formal de pacientes, cobros, gastos ni inventario. Este sistema busca:

1. Centralizar el expediente clínico (historia clínica, odontograma, evolución).
2. Controlar lo cobrado y lo pendiente por paciente y por tratamiento.
3. Dar a cada doctor un tablero de ingresos y egresos, separando los gastos propios de los compartidos (renta, luz, agua, internet, etc.).
4. Generar avisos para que el doctor contacte **manualmente** a sus pacientes por WhatsApp: limpiezas, ajustes y visitas de seguimiento.
5. Integrarse con Google Calendar.
6. Dar a la Dra. Jimena, y solo a ella, un inventario para su pequeño depósito dental, con alertas de caducidad y de stock mínimo.

## 2. Investigación de la competencia (benchmark)

Se revisaron los sistemas más usados en Latinoamérica y España, además de referentes internacionales, para decidir qué funciones son estándar en el mercado y cuáles conviene simplificar para un consultorio de dos doctores.

| Sistema | Origen / mercado | Funciones relevantes observadas | Qué se adopta en este proyecto |
|---|---|---|---|
| **Dentalink** | Chile / LATAM | Agenda, historia clínica digital, odontograma con versiones, presupuestos, control de pagos, gastos, inventario, informes, recordatorios automáticos | Odontograma, presupuestos ligados a pagos, módulo de gastos, informes en el tablero |
| **Dentidesk** | Chile / LATAM | Software en la nube para gestión clínica, administrativa y financiera; confirmación de citas en línea; multi-sucursal | Confirmación de citas (en este proyecto, vía WhatsApp manual) |
| **Clinic Cloud** | España | Odontograma editable en tiempo real, periodontograma, gestión económica | Odontograma interactivo por estados |
| **Dentáctil / Gesden** | España | Presupuestos, consentimientos informados, historia clínica | Registro de consentimiento informado y aviso de privacidad |
| **Medesk / AgendaPro / Doctocliq** | LATAM | Agenda, recordatorios por WhatsApp/SMS, expediente conforme a la NOM-004 | Plantilla de historia clínica alineada a la NOM-004; recordatorios por WhatsApp |
| **Open Dental / Dentrix / Curve** | EE. UU. | Plan de tratamiento por fases, cuentas por cobrar (*aging*), *recall* (rellamado) de higiene, inventario de insumos | Recordatorios de "recall" (limpieza semestral), cuentas por cobrar con antigüedad |
| **Dentronix / Sortly / MedRestock** | Inventario | Alertas de caducidad, stock bajo, valor del inventario, órdenes de compra, campos personalizados | Lotes con caducidad, FEFO, alertas a 60 días, stock mínimo, valor a costo, kardex |

**Conclusiones del benchmark:**

- Todos los sistemas dentales líderes integran **agenda + expediente + odontograma + presupuesto/cobros**. Es el núcleo mínimo.
- Los recordatorios suelen ser automáticos por SMS o WhatsApp Business API, lo cual tiene costo y requiere aprobar plantillas. Como el cliente pidió avisos **manuales**, se usan enlaces `wa.me` con el mensaje ya redactado: no cuesta nada y no requiere cuentas de negocio.
- En inventario, lo que distingue a un sistema real de una simple lista es el **control de caducidad por lote** y las **alertas de stock mínimo**. Para un depósito pequeño basta con un kardex y salidas FEFO; no se necesitan órdenes de compra formales.
- La mayoría de los productos cobran por doctor y por mes. Un desarrollo propio en Render permite mantener el costo cercano a cero en la fase de prueba.

## 3. Actores y permisos

| Actor | Acceso | Notas |
|---|---|---|
| Dra. Jimena Juárez Aguilar | Completo + **Inventario** | Ortodoncista; administra el depósito dental |
| Dr. Juan Carlos Montaño López | Completo, sin inventario | Estética dental |
| Cirujano maxilofacial (externo) | **Sin usuario** | Se agenda como recurso en citas y tratamientos; se le avisa por WhatsApp |
| Paciente | Sin acceso | Recibe mensajes por WhatsApp de forma manual |

## 4. Requisitos funcionales

Prioridad: **A** = imprescindible (incluido en el demo), **B** = deseable (incluido en el demo), **C** = futura versión.

### 4.1 Autenticación y usuarios (RF-AUT)

| ID | Requisito | Prioridad | Estado demo |
|---|---|---|---|
| RF-AUT-01 | Inicio de sesión con usuario y contraseña para cada doctor | A | ✅ |
| RF-AUT-02 | Sesión con expiración (12 h) y cierre de sesión | A | ✅ |
| RF-AUT-03 | Cambio de contraseña por el propio usuario | A | ✅ |
| RF-AUT-04 | Restringir el módulo de inventario a usuarios con permiso (Dra. Jimena) | A | ✅ |
| RF-AUT-05 | Contraseñas almacenadas con hash (PBKDF2-SHA256) | A | ✅ |
| RF-AUT-06 | Bitácora de auditoría (quién modificó qué y cuándo) | C | Parcial: la historia clínica guarda el último editor y la fecha |
| RF-AUT-07 | Autenticación de dos factores | C | ❌ |

### 4.2 Pacientes (RF-PAC)

| ID | Requisito | Prioridad | Estado demo |
|---|---|---|---|
| RF-PAC-01 | Alta, edición y archivado de pacientes (sin borrar su información) | A | ✅ |
| RF-PAC-02 | Ficha de identificación: nombre, nacimiento/edad, sexo, ocupación, domicilio, teléfono, correo, contacto de emergencia o tutor | A | ✅ |
| RF-PAC-03 | Asignar un doctor tratante | A | ✅ |
| RF-PAC-04 | Búsqueda por nombre, teléfono o correo; filtros por doctor y por saldo pendiente | A | ✅ |
| RF-PAC-05 | Mostrar alertas médicas visibles (alergias, diabetes, hipertensión, cardiopatía, coagulación, embarazo) | A | ✅ |
| RF-PAC-06 | Resumen financiero por paciente: presupuestado, pagado y saldo | A | ✅ |
| RF-PAC-07 | Registrar el origen del paciente (Instagram, recomendación…) para medir marketing | B | ✅ |
| RF-PAC-08 | Adjuntar radiografías, fotos y estudios | C | ❌ (requiere almacenamiento S3/Render Disk) |

### 4.3 Historia clínica (RF-HC)

Estructura basada en el contenido mínimo de la **NOM-004-SSA3-2012** (expediente clínico) y en la práctica odontológica de la **NOM-013-SSA2** (prevención y control de enfermedades bucales).

| ID | Requisito | Prioridad | Estado demo |
|---|---|---|---|
| RF-HC-01 | Interrogatorio: motivo de consulta, padecimiento actual, antecedentes heredofamiliares, patológicos y no patológicos, alergias, medicamentos | A | ✅ |
| RF-HC-02 | Condiciones sistémicas como casillas (diabetes, HTA, cardiopatía, coagulopatía, embarazo, tabaquismo, bruxismo) y presión arterial | A | ✅ |
| RF-HC-03 | Exploración extraoral e intraoral, higiene oral y oclusión | A | ✅ |
| RF-HC-04 | **Odontograma interactivo** (numeración FDI, 32 piezas) con estados: sano, caries, obturado, endodoncia, corona/carilla, ausente, por extraer y bracket | A | ✅ |
| RF-HC-05 | Diagnóstico, plan de tratamiento y pronóstico | A | ✅ |
| RF-HC-06 | Registro de consentimiento informado y aviso de privacidad | A | ✅ |
| RF-HC-07 | **Notas de evolución** por visita (procedimiento, piezas, nota, siguiente paso, doctor, fecha) | A | ✅ |
| RF-HC-08 | Vista imprimible / PDF de la historia clínica con espacio para firmas | A | ✅ |
| RF-HC-09 | Periodontograma | C | ❌ |
| RF-HC-10 | Historial de versiones del odontograma | C | ❌ |
| RF-HC-11 | Firma digital del paciente en tableta | C | ❌ |

### 4.4 Agenda y citas (RF-AGE)

| ID | Requisito | Prioridad | Estado demo |
|---|---|---|---|
| RF-AGE-01 | Calendario compartido con vistas de mes, semana, día y lista, con un color por doctor | A | ✅ |
| RF-AGE-02 | Crear una cita con un clic en un horario libre: paciente, doctor, tipo, inicio, duración y notas | A | ✅ |
| RF-AGE-03 | **Asignar al especialista externo (maxilofacial)** a una cita aunque no tenga usuario | A | ✅ |
| RF-AGE-04 | **Detección de empalmes** del doctor y del especialista externo, con opción de forzar | A | ✅ |
| RF-AGE-05 | Estados: programada, confirmada, atendida, cancelada, no asistió | A | ✅ |
| RF-AGE-06 | Al marcar "atendida": nota de evolución, avance de sesiones del tratamiento y recordatorio automático según el tipo de cita | A | ✅ |
| RF-AGE-07 | Duración sugerida según el tipo de cita (p. ej. cirugía: 120 min y maxilofacial preseleccionado) | B | ✅ |
| RF-AGE-08 | Filtrar el calendario por doctor y por especialista externo | B | ✅ |
| RF-AGE-09 | Enviar la confirmación de la cita al paciente y al especialista por WhatsApp (manual) | A | ✅ |
| RF-AGE-10 | Lista de espera y reservación en línea por el paciente | C | ❌ |
| RF-AGE-11 | Control de sillones/gabinetes como recurso | C | ❌ |

### 4.5 Integración con Google Calendar (RF-GCA)

**¿Es posible?** Sí. El sistema ofrece tres niveles:

| ID | Requisito | Prioridad | Estado demo |
|---|---|---|---|
| RF-GCA-01 | Botón "Añadir a Google Calendar" en cada cita (sin configuración) | A | ✅ |
| RF-GCA-02 | **Feed iCal privado por doctor** (`/calendario/<token>.ics`) para suscribirse desde Google Calendar ("Desde URL"); sincroniza en un solo sentido y se refresca automáticamente | A | ✅ |
| RF-GCA-03 | Regenerar el token del feed si se compromete | B | ✅ |
| RF-GCA-04 | **Sincronización inmediata vía Google Calendar API** con cuenta de servicio: crear, actualizar y eliminar eventos al guardar o cancelar citas | B | ✅ (se activa con la variable `GOOGLE_SERVICE_ACCOUNT_JSON`) |
| RF-GCA-05 | Sincronización bidireccional (importar eventos creados en Google) mediante OAuth 2.0 por usuario y *webhooks* `events.watch` | C | ❌ |

### 4.6 Tratamientos, presupuestos y cobros (RF-COB)

| ID | Requisito | Prioridad | Estado demo |
|---|---|---|---|
| RF-COB-01 | Crear un tratamiento o presupuesto: nombre, costo, descuento, sesiones estimadas, doctor y descripción | A | ✅ |
| RF-COB-02 | Estados: presupuesto → en proceso → terminado / cancelado | A | ✅ |
| RF-COB-03 | Registrar **abonos** (monto, fecha, método, referencia) y calcular el saldo automáticamente | A | ✅ |
| RF-COB-04 | Impedir abonos mayores al saldo | A | ✅ |
| RF-COB-05 | Avance clínico (sesiones realizadas / planeadas) y avance de pago (%) | A | ✅ |
| RF-COB-06 | Vincular al especialista externo y sus honorarios; los honorarios se registran como gasto del doctor | A | ✅ |
| RF-COB-07 | Presupuesto imprimible y recibo de pago imprimible (no fiscal) | B | ✅ |
| RF-COB-08 | **Cuentas por cobrar** por doctor y del consultorio, con aviso de saldos sin abono en 30 días o más | A | ✅ |
| RF-COB-09 | Exportar cobros a CSV (Excel) | B | ✅ |
| RF-COB-10 | Facturación electrónica CFDI 4.0 mediante un PAC | C | ❌ |
| RF-COB-11 | Lista de precios / catálogo de tratamientos editable | C | Parcial (sugerencias en el formulario) |

### 4.7 Gastos y finanzas (RF-FIN)

| ID | Requisito | Prioridad | Estado demo |
|---|---|---|---|
| RF-FIN-01 | Registrar gastos con fecha, concepto, categoría, monto, método y quién lo pagó | A | ✅ |
| RF-FIN-02 | Clasificar cada gasto como **propio** o **compartido** | A | ✅ |
| RF-FIN-03 | Reparto configurable de los compartidos (por defecto 50/50) | A | ✅ |
| RF-FIN-04 | **Ajuste entre doctores:** cuánto pagó cada uno de los compartidos frente a lo que le correspondía | B | ✅ |
| RF-FIN-05 | Marcar gastos como recurrentes y copiarlos al mes siguiente con un clic | B | ✅ |
| RF-FIN-06 | Exportar gastos a CSV | B | ✅ |
| RF-FIN-07 | Adjuntar foto del comprobante o factura del gasto | C | ❌ |

### 4.8 Dashboard (RF-DSH)

| ID | Requisito | Prioridad | Estado demo |
|---|---|---|---|
| RF-DSH-01 | Indicadores del mes: ingresos, egresos, utilidad y por cobrar | A | ✅ |
| RF-DSH-02 | Alternar entre **"Mis números"** (doctor) y **"Consultorio"** (ambos) | A | ✅ |
| RF-DSH-03 | Navegar entre meses y comparar contra el mes anterior (%) | A | ✅ |
| RF-DSH-04 | Gráfica de ingresos frente a egresos de los últimos 6 meses | A | ✅ |
| RF-DSH-05 | Gráfica de gastos por categoría | B | ✅ |
| RF-DSH-06 | Avance de tratamientos en proceso (clínico y de pago) | A | ✅ |
| RF-DSH-07 | Citas de hoy y avisos pendientes | A | ✅ |
| RF-DSH-08 | Alertas del depósito dental (solo Dra. Jimena) | A | ✅ |
| RF-DSH-09 | Ingresos del depósito (ventas de mostrador) sumados a los ingresos de la Dra. Jimena | B | ✅ |

### 4.9 Recordatorios y avisos (RF-NOT)

| ID | Requisito | Prioridad | Estado demo |
|---|---|---|---|
| RF-NOT-01 | Centro de avisos con contador en el menú | A | ✅ |
| RF-NOT-02 | Recordatorios a pacientes: limpieza semestral, ajuste mensual de ortodoncia, retenedores, retoque de blanqueamiento, control de carillas, revisión post-quirúrgica, seguimiento de presupuesto | A | ✅ |
| RF-NOT-03 | Creación automática al marcar una cita como atendida (reglas configurables por tipo de cita) | A | ✅ |
| RF-NOT-04 | Creación manual desde el expediente o desde el módulo | A | ✅ |
| RF-NOT-05 | Botón de **WhatsApp con el mensaje redactado**; el doctor lo revisa y lo envía él mismo (no hay envío automático) | A | ✅ |
| RF-NOT-06 | Flujo de estados: pendiente → enviado → completado / descartado (y reabrir) | A | ✅ |
| RF-NOT-07 | Avisos de confirmación de las citas de mañana | A | ✅ |
| RF-NOT-08 | Avisos de saldos atrasados | B | ✅ |
| RF-NOT-09 | Notificaciones *push* o por correo al doctor | C | ❌ |
| RF-NOT-10 | Envío automático por WhatsApp Business API (requiere plantillas aprobadas por Meta y tiene costo) | C | ❌ |

### 4.10 Inventario del depósito dental (RF-INV), exclusivo de la Dra. Jimena

Basado en sistemas como Dentronix, Sortly y MedRestock, adaptado a un depósito pequeño.

| ID | Requisito | Prioridad | Estado demo |
|---|---|---|---|
| RF-INV-01 | Catálogo de productos: SKU, nombre, categoría, marca, unidad, ubicación, proveedor, costo, precio de venta y stock mínimo | A | ✅ |
| RF-INV-02 | Indicar si el producto **tiene caducidad**; en ese caso, cada entrada exige lote y fecha | A | ✅ |
| RF-INV-03 | Control por **lotes** con cantidad, fecha de recepción, caducidad y costo | A | ✅ |
| RF-INV-04 | Entradas de mercancía (compra) | A | ✅ |
| RF-INV-05 | Salidas: **uso en consulta**, **venta de mostrador** (suma a los ingresos) y **merma** | A | ✅ |
| RF-INV-06 | Descuento automático **FEFO** (sale primero lo que caduca primero); bloquear la venta o el uso de lotes caducados | A | ✅ |
| RF-INV-07 | **Alertas de caducidad** (configurable, 60 días por defecto), con semáforo: verde, ámbar ≤ 60 días, rojo < 30 días o caducado | A | ✅ |
| RF-INV-08 | Dar de baja lotes caducados (registra merma) | A | ✅ |
| RF-INV-09 | **Alerta de stock mínimo** y filtro "por reordenar" | A | ✅ |
| RF-INV-10 | Ajuste por conteo físico | B | ✅ |
| RF-INV-11 | **Kardex** de movimientos con filtros | A | ✅ |
| RF-INV-12 | Valor del inventario a costo y margen por producto | B | ✅ |
| RF-INV-13 | Exportar inventario a CSV | B | ✅ |
| RF-INV-14 | Registrar a qué paciente se destinó el material | B | ✅ |
| RF-INV-15 | Órdenes de compra a proveedores y lector de código de barras | C | ❌ |

## 5. Requisitos no funcionales

| ID | Requisito |
|---|---|
| RNF-01 | Interfaz web responsiva (computadora, tableta y celular), en español, con zona horaria America/Mexico_City |
| RNF-02 | Despliegue en un **contenedor Docker** compatible con Render (puerto mediante `$PORT`, *health check* `/healthz`) |
| RNF-03 | Base de datos PostgreSQL en producción (`DATABASE_URL`) y SQLite para desarrollo y demo |
| RNF-04 | Configuración por variables de entorno (sin secretos en el código) |
| RNF-05 | Cookies de sesión firmadas; contenedor ejecutado con un usuario sin privilegios |
| RNF-06 | Tiempo de respuesta menor a 1 s en operaciones comunes con menos de 5,000 pacientes |
| RNF-07 | Protección de datos personales sensibles conforme a la LFPDPPP (aviso de privacidad, acceso restringido) |
| RNF-08 | Conservación del expediente por al menos 5 años (NOM-004); por eso los pacientes se archivan y no se eliminan |
| RNF-09 | Respaldos automáticos de la base de datos (en Render, los ofrece PostgreSQL de pago) |
| RNF-10 | API documentada automáticamente (OpenAPI en `/api/docs`) |

## 6. Reglas de negocio

1. **RN-01:** Ingreso de un doctor = abonos de sus tratamientos + ventas del depósito (si las tiene).
2. **RN-02:** Egreso de un doctor = gastos propios + (gastos compartidos × su % de reparto).
3. **RN-03:** El reparto de gastos compartidos debe sumar 100%.
4. **RN-04:** Un abono no puede exceder el saldo del tratamiento. El primer abono de un presupuesto lo pasa a "en proceso".
5. **RN-05:** Cuando las sesiones realizadas alcanzan las planeadas, el tratamiento pasa a "terminado".
6. **RN-06:** Ni un doctor ni el especialista externo pueden tener dos citas activas que se traslapen, salvo que se fuerce de forma explícita.
7. **RN-07:** Los honorarios del especialista externo se registran como gasto propio del doctor responsable del tratamiento.
8. **RN-08:** Las salidas de inventario usan FEFO y nunca consumen lotes caducados (salvo la merma).
9. **RN-09:** Reglas de recordatorio automático: limpieza → 180 días; ajuste de ortodoncia → 28; blanqueamiento → 180; carillas/coronas → 90; cirugía → 7; valoración → 14.
10. **RN-10:** Los mensajes a pacientes se envían siempre de forma **manual**: el sistema solo prepara el texto.

## 7. Fuera de alcance del demo

Facturación CFDI, pagos en línea, portal de pacientes, archivos e imágenes, periodontograma, roles adicionales (asistente o recepción), multi-sucursal, WhatsApp automático y sincronización bidireccional con Google.

## 8. Fuentes consultadas

- Dentalink: planes y funcionalidades — https://web-es.softwaredentalink.com/en/planes
- Dentalink: uso del odontograma (versionado) — https://intercom.help/softwaredentalink/es/articles/9493218-como-usar-el-odontograma
- Comparativa Dentalink / Dentáctil — https://www.softwaredoit.es/dentalink/dentalink.html , https://www.softwaredoit.es/dentactil/dentactil.html
- Dentidesk (TrustRadius) — https://www.trustradius.com/products/dentidesk/details
- Medesk: software para clínicas dentales — https://www.medesk.net/es/blog/software-para-clinicas-dentales/
- Medesk: NOM del expediente clínico — https://www.medesk.net/es/blog/norma-oficial-mexicana-para-el-expediente-clinico/
- AgendaPro: expediente clínico en México — https://agendapro.com/blog/como-elaborar-un-expediente-clinico-y-cuales-son-sus-implicancias-en-mexico
- Revista ADM: consideraciones normativas del expediente electrónico en odontología — https://www.medigraphic.com/pdfs/adm/od-2022/od225e.pdf
- Comparasoftware: software de odontología en México — https://www.comparasoftware.com/odontologia
- NetSuite: inventario dental — https://www.netsuite.com/portal/resource/articles/inventory-management/dental-inventory-management.shtml
- Sortly (alertas de caducidad y stock bajo) — https://www.sortly.com
- Errores comunes de inventario dental — https://www.methodusa.com/resources/12-common-inventory-management-mistakes-dental-practices-should-avoid
- Google Calendar API con Python (cuenta de servicio) — https://dev.to/joshuaakanetuk/how-to-use-google-calendar-api-with-python-mgp

> Nota: las fuentes de proveedores son material comercial. Las normas oficiales (NOM-004-SSA3-2012, NOM-013-SSA2-2015, NOM-024-SSA3-2012) deben verificarse en el Diario Oficial de la Federación antes de un uso en producción.
