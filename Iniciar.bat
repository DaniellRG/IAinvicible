@echo off
chcp 65001 >nul
title Configuracion - IA Invisible
cd /d "%~dp0"

echo ============================================
echo   CONFIGURACION AUTOMATICA
echo ============================================
echo.

set PYTHON_CMD=

echo [1/4] Buscando Python...

if exist "python_embed\python.exe" set "PYTHON_CMD=%~dp0python_embed\python.exe"
if "%PYTHON_CMD%"=="" if exist "C:\Python314\python.exe" set "PYTHON_CMD=C:\Python314\python.exe"
if "%PYTHON_CMD%"=="" if exist "C:\Python313\python.exe" set "PYTHON_CMD=C:\Python313\python.exe"
if "%PYTHON_CMD%"=="" if exist "C:\Python312\python.exe" set "PYTHON_CMD=C:\Python312\python.exe"
if "%PYTHON_CMD%"=="" if exist "C:\Python311\python.exe" set "PYTHON_CMD=C:\Python311\python.exe"
if "%PYTHON_CMD%"=="" if exist "C:\Python310\python.exe" set "PYTHON_CMD=C:\Python310\python.exe"

if not "%PYTHON_CMD%"=="" echo [OK] Python encontrado. & goto :check_deps

echo.
echo [!] Python no encontrado.
echo [2/4] Descargando Python portable...
echo.

if not exist "python_embed" mkdir python_embed

echo Descargando Python 3.12...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.4/python-3.12.4-embed-amd64.zip' -OutFile 'python_embed\python.zip'"
if not exist "python_embed\python.zip" echo ERROR: Sin conexion. & pause & exit /b 1

echo Extrayendo...
powershell -Command "Expand-Archive -Path 'python_embed\python.zip' -DestinationPath 'python_embed' -Force"
del "python_embed\python.zip" 2>nul

echo Configurando...
powershell -Command "$c = Get-Content 'python_embed\python312._pth'; $c = $c -replace '#import site','import site'; Set-Content 'python_embed\python312._pth' $c"

echo Descargando pip...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'python_embed\get-pip.py'"
python_embed\python.exe python_embed\get-pip.py
del "python_embed\get-pip.py" 2>nul

set "PYTHON_CMD=%~dp0python_embed\python.exe"
echo [OK] Python portable instalado.

:check_deps
echo.
echo [3/4] Verificando dependencias...

%PYTHON_CMD% -c "import PyQt6" >nul 2>&1
if errorlevel 1 goto :install_pyqt
echo [OK] PyQt6
goto :check_llama

:install_pyqt
echo Instalando PyQt6...
%PYTHON_CMD% -m pip install PyQt6
echo [OK] PyQt6 instalado.

:check_llama
%PYTHON_CMD% -c "import llama_cpp" >nul 2>&1
if errorlevel 1 goto :install_llama
echo [OK] llama-cpp-python
goto :check_requests

:install_llama
echo Instalando llama-cpp-python (puede tardar)...
%PYTHON_CMD% -m pip install llama-cpp-python
echo [OK] llama-cpp-python instalado.

:check_requests
%PYTHON_CMD% -c "import requests" >nul 2>&1
if errorlevel 1 goto :install_requests
echo [OK] requests
goto :done

:install_requests
echo Instalando requests...
%PYTHON_CMD% -m pip install requests
echo [OK] requests instalado.

:done
echo.
echo ============================================
echo   CONFIGURACION COMPLETADA
echo ============================================
echo.
echo Iniciando programa...
echo.

start "" "%PYTHON_CMD%" "%~dp0main.py"
pause
