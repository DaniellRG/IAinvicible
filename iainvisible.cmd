@echo off
cd /d "%~dp0"

set "PYW="
if exist "%~dp0python_embed\pythonw.exe" set "PYW=%~dp0python_embed\pythonw.exe"
if "%PYW%"=="" if exist "%~dp0python_embed\python.exe" set "PYW=%~dp0python_embed\python.exe"
if exist "%~dp0..\..\pythonw.exe" set "PYW=%~dp0..\..\pythonw.exe"

if "%PYW%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe" set "PYW=%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"
if "%PYW%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" set "PYW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
if "%PYW%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" set "PYW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if "%PYW%"=="" if exist "C:\Python314\pythonw.exe" set "PYW=C:\Python314\pythonw.exe"
if "%PYW%"=="" if exist "C:\Python313\pythonw.exe" set "PYW=C:\Python313\pythonw.exe"
if "%PYW%"=="" if exist "C:\Python312\pythonw.exe" set "PYW=C:\Python312\pythonw.exe"
if "%PYW%"=="" if exist "C:\Python311\pythonw.exe" set "PYW=C:\Python311\pythonw.exe"
if "%PYW%"=="" if exist "C:\Python310\pythonw.exe" set "PYW=C:\Python310\pythonw.exe"

if "%PYW%"=="" (
    echo No se encontro Python. Instalalo desde python.org
    pause
    exit /b 1
)

start "" "%PYW%" "%~dp0main.py"