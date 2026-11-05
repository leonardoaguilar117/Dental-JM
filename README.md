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

1. Sube el proyecto a GitHub.
2. En Render, ve a **New → Blueprint** y elige el repositorio. Render usa `render.yaml` para crear el servicio Docker y la base PostgreSQL.
3. Cuando termine el despliegue, entra con `jimena / demo123` y cambia las contraseñas.

En `.env.example` están las variables disponibles (Google Calendar, alertas, zona horaria).

## Regenerar el PDF

```bash
pip install reportlab
python docs/generar_manual.py
```
