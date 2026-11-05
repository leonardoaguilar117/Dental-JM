@echo off
setlocal
chcp 65001 >nul
title Consultorio Dental JM - servidor local
cd /d "%~dp0"

echo ============================================
echo   Consultorio Dental JM - ejecucion local
echo ============================================
echo.

rem --- 1. Verificar Python ---
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No se encontro Python. Instalalo desde https://www.python.org/downloads/
    echo         y marca la casilla "Add Python to PATH".
    pause
    exit /b 1
)

rem --- 2. Reiniciar datos demo si se pide: run_local.bat reset ---
if /i "%~1"=="reset" (
    if exist "data\crm_dental.db" (
        del /q "data\crm_dental.db"
        echo [OK] Base de datos local borrada. Se recargaran los datos demo.
    )
)

rem --- 3. Crear entorno virtual (solo la primera vez) ---
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creando entorno virtual .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
)

rem --- 4. Instalar dependencias (solo si cambio requirements.txt) ---
set "STAMP=.venv\requirements.stamp"
fc /b requirements.txt "%STAMP%" >nul 2>nul
if errorlevel 1 (
    echo [2/3] Instalando dependencias, puede tardar un par de minutos ...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip -q
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt -q
    if errorlevel 1 (
        echo [ERROR] Fallo la instalacion de dependencias.
        pause
        exit /b 1
    )
    copy /y requirements.txt "%STAMP%" >nul
) else (
    echo [2/3] Dependencias ya instaladas.
)

rem --- 5. Variables de entorno locales (SQLite en .\data) ---
set "SECRET_KEY=clave-local-solo-para-pruebas"
set "SEED_DEMO=true"
set "DATABASE_URL="
set "PORT=8000"

echo [3/3] Iniciando servidor en http://localhost:%PORT%
echo.
echo   Usuarios demo:  jimena / demo123   (con inventario)
echo                   carlos / demo123
echo   API docs:       http://localhost:%PORT%/api/docs
echo.
echo   Para detener el servidor presiona Ctrl+C.
echo   Para reiniciar los datos demo:  run_local.bat reset
echo.

rem Abre el navegador unos segundos despues de arrancar
start "" /min cmd /c "timeout /t 4 >nul & start http://localhost:%PORT%"

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port %PORT% --reload

echo.
echo Servidor detenido.
pause
endlocal
