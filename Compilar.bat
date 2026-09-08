@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Compilando programa...

rem Nombre del ejecutable generado (sin .exe). Cambialo aqui si quieres otro.
set "NOMBRE=svchost"

echo ============================================
echo   COMPILANDO EJECUTABLE PORTABLE
echo ============================================
echo.

echo [1/3] Verificando PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando PyInstaller...
    python -m pip install pyinstaller
)

echo [2/3] Compilando (esto puede tardar 2-5 minutos)...
python -m PyInstaller ^
    --name "%NOMBRE%" ^
    --onefile ^
    --windowed ^
    --noconfirm ^
    --clean ^
    --add-data "ui;ui" ^
    --add-data "core;core" ^
    --add-data "utils;utils" ^
    --add-data "config.json;." ^
    --hidden-import "PyQt6" ^
    --hidden-import "PyQt6.QtWidgets" ^
    --hidden-import "PyQt6.QtCore" ^
    --hidden-import "PyQt6.QtGui" ^
    --collect-all "llama_cpp" ^
    --hidden-import "requests" ^
    --exclude-module "torch" ^
    --exclude-module "torchvision" ^
    --exclude-module "torchaudio" ^
    --exclude-module "transformers" ^
    --exclude-module "tensorflow" ^
    --exclude-module "tensorboard" ^
    --exclude-module "scipy" ^
    --exclude-module "pandas" ^
    --exclude-module "matplotlib" ^
    --exclude-module "cv2" ^
    --exclude-module "yt_dlp" ^
    --exclude-module "onnxruntime" ^
    --exclude-module "soundfile" ^
    --exclude-module "av" ^
    --exclude-module "lxml" ^
    --exclude-module "sympy" ^
    --exclude-module "openpyxl" ^
    --exclude-module "pytest" ^
    --exclude-module "rich" ^
    --exclude-module "websockets" ^
    --exclude-module "mutagen" ^
    --exclude-module "brotli" ^
    --exclude-module "curl_cffi" ^
    --exclude-module "secretstorage" ^
    launcher.py

echo.
echo [3/3] Moviendo ejecutable...
if exist "dist\%NOMBRE%.exe" (
    move /Y "dist\%NOMBRE%.exe" "%NOMBRE%.exe"
    echo.
    echo ============================================
    echo   COMPILACION COMPLETADA!
    echo ============================================
    echo.
    echo Ejecutable: %NOMBRE%.exe
    echo Tamano: 
    for %%A in (%NOMBRE%.exe) do echo   %%~zA bytes
    echo.
    echo Copia este archivo a tu USB y ejecutalo.
    echo No necesitas instalar nada mas.
    echo ============================================
) else (
    echo.
    echo [ERROR] No se genero el ejecutable.
    echo Revisa los errores arriba.
)
echo.
pause
