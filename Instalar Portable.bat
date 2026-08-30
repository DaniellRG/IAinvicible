@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Creando paquete portable...

echo ============================================
echo   CREANDO PAQUETE PORTABLE
echo ============================================
echo.

echo [1/3] Creando carpeta portable...
if not exist "portable" mkdir portable
if not exist "portable\models" mkdir portable\models

echo [2/3] Copiando archivos...
xcopy /E /I /Y "core" "portable\core" >nul
xcopy /E /I /Y "ui" "portable\ui" >nul
xcopy /E /I /Y "utils" "portable\utils" >nul
xcopy /E /I /Y "models" "portable\models" >nul
copy /Y "main.py" "portable\main.py" >nul
copy /Y "config.json" "portable\config.json" >nul
copy /Y "Iniciar.bat" "portable\Iniciar.bat" >nul
copy /Y "Iniciar.vbs" "portable\Iniciar.vbs" >nul

echo [3/3] Listo!
echo.
echo ============================================
echo   CARPETA "portable" LISTA
echo ============================================
echo.
echo Copia la carpeta "portable" a tu USB.
echo En la otra PC, ejecuta "Iniciar.bat" y
echo hara todo automaticamente.
echo ============================================
echo.
pause
