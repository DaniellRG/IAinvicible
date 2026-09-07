@echo off
chcp 65001 >nul
title Configuracion - IA Invisible
cd /d "%~dp0"

echo ============================================
echo   CONFIGURACION AUTOMATICA
echo ============================================
echo.

set "PYTHON_CMD="

echo [1/4] Buscando Python...

if exist "%~dp0python_embed\python.exe" set "PYTHON_CMD=%~dp0python_embed\python.exe"
if "%PYTHON_CMD%"=="" if exist "C:\Python314\python.exe" set "PYTHON_CMD=C:\Python314\python.exe"
if "%PYTHON_CMD%"=="" if exist "C:\Python313\python.exe" set "PYTHON_CMD=C:\Python313\python.exe"
if "%PYTHON_CMD%"=="" if exist "C:\Python312\python.exe" set "PYTHON_CMD=C:\Python312\python.exe"
if "%PYTHON_CMD%"=="" if exist "C:\Python311\python.exe" set "PYTHON_CMD=C:\Python311\python.exe"
if "%PYTHON_CMD%"=="" if exist "C:\Python310\python.exe" set "PYTHON_CMD=C:\Python310\python.exe"

if not "%PYTHON_CMD%"=="" echo [OK] Python encontrado. & goto :setup_pip

echo.
echo [!] Python no encontrado.
echo Descargando Python portable...
echo.

if not exist "python_embed" mkdir python_embed

echo Descargando Python 3.12...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.4/python-3.12.4-embed-amd64.zip' -OutFile 'python_embed\python.zip'"
if not exist "python_embed\python.zip" (
    echo.
    echo ERROR: No se pudo descargar Python. Revisa tu conexion a internet.
    pause
    exit /b 1
)

echo Extrayendo...
powershell -Command "Expand-Archive -Path 'python_embed\python.zip' -DestinationPath 'python_embed' -Force"
del "python_embed\python.zip" 2>nul

echo Configurando...
powershell -Command "$c = Get-Content 'python_embed\python312._pth'; $c = $c -replace '#import site','import site'; Set-Content 'python_embed\python312._pth' $c"

set "PYTHON_CMD=%~dp0python_embed\python.exe"
echo [OK] Python portable instalado.

:setup_pip
"%PYTHON_CMD%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo Instalando pip...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py'"
    "%PYTHON_CMD%" get-pip.py
    del "get-pip.py" 2>nul
)

echo.
echo [2/4] Verificando dependencias...
"%PYTHON_CMD%" -c "import PyQt6, httpx, requests" >nul 2>&1
if not errorlevel 1 goto :deps_ok

echo.
echo Faltan dependencias. Intentando instalarlas...
if not exist "%~dp0requirements.txt" (
    echo.
    echo ERROR: No se encuentra requirements.txt junto al programa.
    pause
    exit /b 1
)
"%PYTHON_CMD%" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo.
    echo ERROR: No se pudieron instalar las dependencias.
    echo Si esta PC no tiene internet, copia tambien la carpeta
    echo "python_embed" (ya configurada) junto al programa.
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas.
goto :check_llama

:deps_ok
echo [OK] PyQt6, httpx y requests ya disponibles.

rem ============================================
rem  llama-cpp-python es OPCIONAL (modelos .gguf).
rem  Si no se instala, la app funciona sin GGUF.
rem ============================================
:check_llama
"%PYTHON_CMD%" -c "import llama_cpp" >nul 2>&1
if errorlevel 1 (
    echo Instalando llama-cpp-python (opcional, puede tardar)...
    "%PYTHON_CMD%" -m pip install llama-cpp-python >nul 2>&1
    if errorlevel 1 (
        echo [AVISO] llama-cpp-python NO se instalo. La app funcara sin modelos .gguf.
    ) else (
        echo [OK] llama-cpp-python instalado.
    )
) else (
    echo [OK] llama-cpp-python ya disponible.
)

echo.
echo ============================================
echo   CONFIGURACION COMPLETADA
echo ============================================
echo.
echo Iniciando programa...
echo.

start "" "%PYTHON_CMD%" "%~dp0main.py"
pause