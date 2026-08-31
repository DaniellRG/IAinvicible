@echo off
chcp 65001 >nul
title Instalador Global - IA Invisible
cd /d "%~dp0"
setlocal

set "APPDIR=%LOCALAPPDATA%\Programs\IAInvisible"

echo ============================================
echo   INSTALADOR GLOBAL - IA INVISIBLE
echo ============================================
echo.

echo [1/3] Copiando archivos a %APPDIR% ...
if not exist "%APPDIR%" mkdir "%APPDIR%"
if not exist "%APPDIR%\models" mkdir "%APPDIR%\models"
xcopy /E /I /Y "core" "%APPDIR%\core" >nul
xcopy /E /I /Y "ui" "%APPDIR%\ui" >nul
xcopy /E /I /Y "utils" "%APPDIR%\utils" >nul
xcopy /E /I /Y "models" "%APPDIR%\models" >nul
copy /Y "main.py" "%APPDIR%\main.py" >nul
copy /Y "launcher.py" "%APPDIR%\launcher.py" >nul
copy /Y "iainvisible.cmd" "%APPDIR%\iainvisible.cmd" >nul
echo     [OK] Archivos copiados.

echo [2/3] Agregando a PATH del usuario...
powershell -Command "$path='%APPDIR%'; $p=[Environment]::GetEnvironmentVariable('Path','User'); if(($p -split ';') -notcontains $path){ [Environment]::SetEnvironmentVariable('Path', $p.TrimEnd(';')+';'+$path, 'User'); Write-Host 'Agregado a PATH.' } else { Write-Host 'Ya estaba en PATH.' }"
echo     [OK]

echo [3/3] Verificando instalacion...
if exist "%APPDIR%\iainvisible.cmd" (
    echo     [OK] Comando "iainvisible" instalado.
) else (
    echo     [ERROR] No se pudo crear el comando.
)

echo.
echo ============================================
echo   INSTALACION COMPLETADA
echo ============================================
echo.
echo Cierra esta ventana, abre una NUEVA ventana
echo de cmd y escribe:
echo.
echo     iainvisible
echo.
echo para abrir el programa desde cualquier lugar.
echo ============================================
echo.
pause