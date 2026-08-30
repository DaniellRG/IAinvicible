@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Compilando programa...

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
    --name "IA_Invisible" ^
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
    --hidden-import "llama_cpp" ^
    --hidden-import "requests" ^
    launcher.py

echo.
echo [3/3] Moviendo ejecutable...
if exist "dist\IA_Invisible.exe" (
    move /Y "dist\IA_Invisible.exe" "IA_Invisible.exe"
    echo.
    echo ============================================
    echo   COMPILACION COMPLETADA!
    echo ============================================
    echo.
    echo Ejecutable: IA_Invisible.exe
    echo Tamano: 
    for %%A in (IA_Invisible.exe) do echo   %%~zA bytes
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
