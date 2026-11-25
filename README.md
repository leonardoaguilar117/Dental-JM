# Consultorio Dental JM (demo)

Sistema de gestión para el consultorio de la **Dra. Jimena Juárez Aguilar** (ortodoncia + depósito dental) y el **Dr. Juan Carlos Montaño López** (estética dental). Está hecho con FastAPI y listo para Docker y Render.

- 📘 Manual con el funcionamiento y el flujo de trabajo: [`docs/Manual_Consultorio_Dental_JM.pdf`](docs/Manual_Consultorio_Dental_JM.pdf)
- 📋 Requisitos funcionales y comparación con la competencia: [`docs/REQUISITOS_FUNCIONALES.md`](docs/REQUISITOS_FUNCIONALES.md)
- 🖼️ Capturas: [`docs/capturas/`](docs/capturas)

## Usuarios demo

| Usuario | Contraseña | Rol |
|---|---|---|
| `jimena` | `demo123` | Ortodoncia + inventario |
| `carlos` | `demo123` | Estética dental |

Con `SEED_DEMO=true`, la primera vez que arranca con la base vacía carga datos ficticios.

## Historia clínica y cumplimiento (COFEPRIS)

La historia clínica sigue la NOM-004-SSA3-2012 (expediente clínico) y la NOM-013-SSA2-2015 (salud bucal): ficha de identificación (CURP, estado civil, lugar de nacimiento), interrogatorio con antecedentes y aparatos y sistemas, habitus exterior y signos vitales, exploración de cabeza/cuello/ATM/boca, odontograma con CPOD, índice de placa, estudios de laboratorio y gabinete, diagnóstico, pronóstico e indicación terapéutica, notas de evolución/interconsulta/referencia (no editables; se corrige con nota aclaratoria) con nombre y cédula del médico, carta de consentimiento con acto autorizado, riesgos, testigos y firma, aviso de privacidad y bitácora de accesos y cambios. Captura tu cédula en Configuración y los datos del establecimiento (`CLINIC_*`, licencia sanitaria, responsable sanitario) en las variables de entorno. Es una herramienta de apoyo: revisa con tu responsable sanitario que cubre lo que pide tu autoridad local.

## Seguridad

En producción (`ENVIRONMENT=production`, que Render activa solo) la app exige un `SECRET_KEY` propio, usa cookies solo por HTTPS, oculta `/api/docs`, bloquea 10 min tras 5 intentos fallidos de acceso, valida el origen de cada formulario (anti-CSRF), envía cabeceras de seguridad y no guarda en caché los datos clínicos. Las contraseñas nuevas requieren 10 caracteres. En producción las cuentas demo reciben una contraseña aleatoria (se imprime una vez en el log) o la de `DEMO_PASSWORD`.

## Ejecutar localmente

**Windows (lo más fácil):** haz doble clic en `run_local.bat`. Crea el entorno, instala las dependencias, arranca el servidor y abre el navegador. Para empezar con datos demo limpios: `run_local.bat reset`.

Manual:

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
# http://localhost:8000   ·  API: http://localhost:8000/api/docs
```

## Docker

```bash
docker build -t consultorio-jm .
docker run -p 8000:8000 -e SECRET_KEY=algo-secreto consultorio-jm
```

## Render

La base de datos (SQLite) vive dentro del contenedor, en un **disco persistente** de Render montado en `/var/data`: así sobrevive despliegues y reinicios. Los discos persistentes requieren un plan de pago (Starter o superior).

**Opción A, servicio nuevo con Blueprint:** **New → Blueprint**, elige el repositorio. `render.yaml` crea el servicio Docker (plan Starter, rama `main`, despliegue automático), el disco `datos` en `/var/data` y una `SECRET_KEY` aleatoria. Solo pedirá `DEMO_PASSWORD`.

**Opción B, servicio que ya existe:**

1. **Settings → Instance Type:** Starter (o superior).
2. **Disks → Add Disk:** nombre `datos`, *Mount Path* `/var/data`, tamaño 1 GB.
3. **Environment:**

| Variable | Valor |
|---|---|
| `DATA_DIR` | `/var/data` |
| `SECRET_KEY` | botón **Generate** (aleatoria, ≥ 32 caracteres) |
| `DEMO_PASSWORD` | contraseña inicial de `jimena` y `carlos` (≥ 10 caracteres) |
| `SEED` | `inicial` (doctores + 4 pacientes) o `demo` (demostración completa) |

En producción la app no arranca si falta `SECRET_KEY` o si `DATA_DIR` no apunta a un disco donde pueda escribir; el log dice exactamente qué falta. `DEMO_PASSWORD` solo se usa la primera vez, al crear las cuentas; después cada doctor cambia su contraseña en Configuración. Si algún día prefieres PostgreSQL, define `DATABASE_URL` y la app la usa en lugar del archivo.

En `.env.example` están todas las variables (Google Calendar, alertas, zona horaria, datos del establecimiento).

## Regenerar el PDF

```bash
pip install reportlab
python docs/generar_manual.py
```
