# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Los dos doctores del Consultorio Dental JM, que son los únicos usuarios:

- **Dra. Jimena Juárez Aguilar**: ortodoncia; además lleva el depósito dental.
- **Dr. Juan Carlos Montaño López**: estética dental.

Usan el sistema ellos mismos, entre pacientes, en la computadora del consultorio y en el celular. Ellos agendan, confirman, cobran y llenan la historia clínica. No hay recepcionista ni asistente.

## Product Purpose

Sistema de gestión del consultorio: agenda, pacientes, historia clínica, tratamientos, finanzas por doctor, recordatorios por WhatsApp y depósito dental.

Tiene éxito cuando:

1. **Nadie falta a su cita**: los recordatorios y las confirmaciones por WhatsApp salen a tiempo.
2. **El expediente está en regla**: la historia clínica cumple con la NOM-004-SSA3-2012 y la NOM-013-SSA2-2015 (COFEPRIS).

## Operating Context

- Lo usan dos doctores a la vez; cada uno ve sus propios números, y hay gastos compartidos entre ambos.
- Todo es en español de México (fechas, moneda MXN, zona horaria local).
- Los mensajes salen por enlaces de WhatsApp (wa.me); las citas se sincronizan con Google Calendar.
- Las notas de evolución no se editan; se corrigen con una nota aclaratoria. Llevan el nombre y la cédula del médico.
- Se despliega en Render (Docker + PostgreSQL); en local corre con `run_local.bat` (uvicorn en el puerto 8000).

## Capabilities and Constraints

- Stack existente: FastAPI + plantillas Jinja2 + CSS y JS sin frameworks (sin paso de compilación). Three.js por CDN para el 3D (molar del inicio, tipodonto del paciente), Chart.js para gráficas y FullCalendar para la agenda.
- Módulos: inicio, agenda, pacientes (historia clínica, odontograma y tipodonto 3D, consentimiento con firma, bitácora), finanzas (cobros, saldos, egresos), recordatorios y avisos, depósito (inventario, lotes, caducidades) y configuración.
- Seguridad en producción: anti-CSRF, bloqueo tras intentos fallidos, sin caché en datos clínicos.

## Brand Commitments

- Logo Dental JM (diente en dos trazos) y paleta Lavanda: #012880, #85B559, #A393BE, #C0CDE6, con tema claro y oscuro.
- Nunca inventar datos, testimonios, reseñas ni cifras: solo información real del consultorio. Los datos demo son ficticios y se dicen así.

## Evidence on Hand

- Logo del consultorio (recreado en SVG en `app/templates/_icons.html`, macro `logo`).
- Manual: `docs/Manual_Consultorio_Dental_JM.pdf`; requisitos: `docs/REQUISITOS_FUNCIONALES.md`; capturas: `docs/capturas/`.
- No hay testimonios, reseñas ni fotos de pacientes reales; no se deben fabricar.

## Product Principles

1. Lo que evita una falta va primero: la próxima cita, las confirmaciones y los recordatorios están a un toque.
2. El expediente clínico es un documento legal: nada que lo altere sin dejar rastro.
3. Dos doctores, un consultorio: cada uno ve lo suyo sin perder lo compartido.
4. Pensado para usarse entre pacientes: rápido en el celular, con poco que leer.
