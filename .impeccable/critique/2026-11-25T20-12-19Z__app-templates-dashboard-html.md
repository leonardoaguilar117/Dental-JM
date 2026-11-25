---
target: inicio (dashboard)
total_score: 22
max_score: 40
na_heuristics: 
p0_count: 1
p1_count: 2
target_identity: "file:C:\\Users\\leona\\Downloads\\CRM Dental JM - Proyecto 6\\app\\templates\\dashboard.html"
target_fingerprint: "sha256:b6abb547f59f08cbe545befa7934137e743628fbca360ea70d574d11459ae158"
target_path: "C:\\Users\\leona\\Downloads\\CRM Dental JM - Proyecto 6\\app\\templates\\dashboard.html"
timestamp: 2026-11-25T20-12-19Z
slug: app-templates-dashboard-html
---
Method: dual-agent (A: revisión de diseño · B: detector + navegador)

## Design Health Score
| # | Heurística | Puntos | Hallazgo clave |
|---|---|---|---|
| 1 | Visibilidad del estado | 2 | El chip "4 citas por atender hoy" convive con "Próxima cita: Sin citas pendientes"; "Tu semana" dice "4 citas por delante" aunque ya pasaron y no se cerraron. |
| 2 | Lenguaje del mundo real | 3 | Buen español de México; pero "Por avisar hoy" muestra avisos "vencido hace 23 días". |
| 3 | Control y libertad | 2 | "Enviar" abre WhatsApp y al volver nada se marca como enviado ni se puede posponer. |
| 4 | Consistencia | 2 | Marino en héroe, "Registrar gasto", chip de hoy y tarjetas del feed: rompe la regla "un solo momento marino". Dos caminos para enviar. |
| 5 | Prevención de errores | 3 | Pantalla de bajo riesgo. |
| 6 | Reconocer, no recordar | 2 | Dock solo con íconos en reposo; burbujas 4/27/15/42 sin significado explícito. |
| 7 | Flexibilidad y eficiencia | 2 | Sin envío en lote ni "ver todos" en el feed (tope de 7). |
| 8 | Estética y minimalismo | 2 | 11 secciones; la primera tarjeta del feed gasta ~200 px en líneas decorativas. |
| 9 | Recuperación de errores | 2 | Sin estado para paciente sin teléfono, ni si falla el 3D o la gráfica. |
| 10 | Ayuda | 2 | La única pista es "Mueve el cursor". |
| **Total** | | **22/40** | Aceptable, con problemas importantes |

## Design Specificity Verdict
Parcialmente específico. Arriba es inconfundiblemente Dental JM (logo, Lavanda, molar 3D, saludo, chips de semana, jornada por doctor). Abajo se vuelve un tablero SaaS genérico (KPIs, gráfica de 6 meses, gastos, tabla de tratamientos). El bloque más importante para el éxito del producto (avisos por WhatsApp) usa el diseño menos propio: el color de cada tarjeta depende de su posición, no de su urgencia.

Detector: 15 hallazgos en CLI, 4 en navegador (escritorio), 1 en celular, 10 en la ficha del paciente. Reales: burbujas de conteo a 10.5 px, iniciales blancas sobre #418d96 (3.8:1). Falsos positivos: cuadrícula del feed (componente pedido), rayado de citas canceladas y líneas de hora (funcionales), barra de tiempo del aviso, contraste 1.3:1 en hover (lectura estática), negro en el delta. Advertencia de three.js (PCFSoftShadowMap) ya corregida.

## Priority Issues
1. [P0] Estado de citas contradictorio: chip "4 por atender" vs "Sin citas pendientes". Separar "sin marcar" de "próximas"; chip "4 citas sin marcar · Cerrar"; excluir citas pasadas de "por delante". → /impeccable clarify
2. [P1] El feed de WhatsApp es el trabajo principal pero usa estilo prestado y 8–10 líneas por tarjeta; botón Enviar de 28 px. Lista compacta (nombre · motivo · vencido · Enviar de 44 px), vencidos primero, "Ver todos", marcar enviado; subirlo justo bajo el héroe y convertir el botón del héroe en envío en lote. → /impeccable distill + /impeccable layout
3. [P1] En el celular la primera pantalla es el diente 3D; la jornada tiene citas ilegibles de 23 px y la tabla de tratamientos ocupa ~360 px por renglón. Achicar el molar, abrir con próxima cita y avisos, jornada como lista vertical, tratamientos como enlace. → /impeccable adapt
4. [P2] Demasiado marino: "Registrar gasto" a cielo, tarjetas del feed sobre blanco. → /impeccable quieter
5. [P2] KPIs de dinero sin contexto (-87.2 % el día 25): comparar contra el mismo día del mes pasado o rotular "mes en curso"; mover gráfica y gastos a Finanzas. → /impeccable clarify

## Persona Red Flags
- Doctora entre pacientes: debe bajar por héroe, accesos y semana para llegar a "Enviar"; sin envío en lote ni marca de enviado, reenvía u olvida.
- Usuario poco técnico: dock solo con íconos y burbujas sin explicación; "Mueve el cursor" invita a jugar con el diente.
- Celular a una mano: acciones a media página; "Enviar" pequeño y a la izquierda; "Registrar gasto" huérfano a todo lo ancho.

## Minor Observations
Fecha repetida (encabezado y héroe); "Avance ·" con punto colgando en el celular; chip de lotes caducados repite la alerta del depósito; la entrada con difuminado deja tarjetas borrosas a media animación al hacer scroll; estilo en línea en "Sin citas hoy"; navegación de mes lejos de los KPIs en el celular.

## Questions to Consider
- Si en el celular el inicio mostrara un solo bloque, ¿sería el diente o "a quién le escribo ahora"?
- ¿El inicio debe ser el día del consultorio (ambos doctores) y las finanzas vivir solo en Finanzas?
- ¿Cómo se ve "terminé por hoy"? ¿Hay un estado final que la doctora pueda alcanzar?
