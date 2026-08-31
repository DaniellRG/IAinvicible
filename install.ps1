$ErrorActionPreference = 'Continue'
$repoUrl = 'https://codeload.github.com/DaniellRG/IAinvicible/zip/refs/heads/main'
$appDir  = Join-Path $env:LOCALAPPDATA 'IAInvisible'
$tmpDir  = Join-Path $env:TEMP ('iainvis_' + [guid]::NewGuid().ToString('N'))

Write-Host ''
Write-Host '============================================'
Write-Host '   INSTALLING IA INVISIBLE'
Write-Host '============================================'
Write-Host ''
Write-Host '   It may take a few minutes...'
Write-Host ''

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# ---------------------------------------------------------------
Write-Host '[1/5] Downloading program...'
# ---------------------------------------------------------------
New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
$zip = Join-Path $tmpDir 'program.zip'
Invoke-WebRequest -Uri $repoUrl -OutFile $zip
Expand-Archive -Path $zip -DestinationPath $tmpDir -Force
Remove-Item $zip

$src = Get-ChildItem -Path $tmpDir -Directory | Select-Object -First 1

if (Test-Path $appDir) { Remove-Item -Recurse -Force $appDir }
New-Item -ItemType Directory -Force -Path $appDir | Out-Null
Copy-Item -Recurse -Force (Join-Path $src.FullName '*') $appDir
Write-Host '   [OK] Downloaded.'

# ---------------------------------------------------------------
# Find Python (avoid Microsoft Store stub)
# ---------------------------------------------------------------
function Test-RealPython($path) {
    if (-not (Test-Path $path)) { return $false }
    try {
        $v = & $path -c 'import sys; sys.stdout.write(sys.version.split()[0])' 2>$null
        return $v -match '^3\.'
    } catch { return $false }
}

$cmd = $null
foreach ($p in @(
    'C:\Python314\python.exe',
    'C:\Python313\python.exe',
    'C:\Python312\python.exe',
    'C:\Python311\python.exe',
    'C:\Python310\python.exe'
)) {
    if (Test-RealPython $p) { $cmd = $p; break }
}
if (-not $cmd) {
    foreach ($p in @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python314\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python310\python.exe')
    )) {
        if (Test-RealPython $p) { $cmd = $p; break }
    }
}

$embedDir = Join-Path $appDir 'python_embed'

if (-not $cmd) {
    Write-Host '[2/5] Python not found. Downloading portable Python...'
    New-Item -ItemType Directory -Force -Path $embedDir | Out-Null
    $pyZip = Join-Path $env:TEMP 'pyemb.zip'
    Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.4/python-3.12.4-embed-amd64.zip' -OutFile $pyZip
    Expand-Archive -Path $pyZip -DestinationPath $embedDir -Force
    Remove-Item $pyZip

    $pth = Join-Path $embedDir 'python312._pth'
    if (Test-Path $pth) {
        (Get-Content $pth) -replace '#import site', 'import site' | Set-Content $pth
    }

    $gp = Join-Path $env:TEMP 'get-pip.py'
    Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile $gp
    & (Join-Path $embedDir 'python.exe') $gp | Out-Null
    Remove-Item $gp

    $cmd = Join-Path $embedDir 'python.exe'
    Write-Host '   [OK] Python downloaded.'
} else {
    Write-Host '[2/5] Python found.'
}

# ---------------------------------------------------------------
Write-Host '[3/5] Installing dependencies (this takes a while)...'
# ---------------------------------------------------------------
function Install-Dep($mod) {
    $ok = & $cmd -c "import $mod" 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $cmd -m pip install $mod
    }
}
Install-Dep 'PyQt6'
Install-Dep 'requests'
Install-Dep 'llama_cpp'

# ---------------------------------------------------------------
Write-Host '[4/5] Creating command "iainvisible"...'
# ---------------------------------------------------------------
$launcher = Join-Path $appDir 'iainvisible.cmd'
$content = @'
@echo off
cd /d "%~dp0"
set "PYW="
if exist "%~dp0python_embed\pythonw.exe" set "PYW=%~dp0python_embed\pythonw.exe"
if "%PYW%"=="" if exist "%~dp0python_embed\python.exe" set "PYW=%~dp0python_embed\python.exe"
if "%PYW%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe" set "PYW=%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"
if "%PYW%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" set "PYW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
if "%PYW%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" set "PYW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if "%PYW%"=="" if exist "C:\Python314\pythonw.exe" set "PYW=C:\Python314\pythonw.exe"
if "%PYW%"=="" if exist "C:\Python313\pythonw.exe" set "PYW=C:\Python313\pythonw.exe"
if "%PYW%"=="" if exist "C:\Python312\pythonw.exe" set "PYW=C:\Python312\pythonw.exe"
if "%PYW%"=="" (
    echo No Python found. Re-run the install command.
    pause
    exit /b 1
)
start "" "%PYW%" "%~dp0main.py"
'@
Set-Content -Path $launcher -Value $content -Encoding ASCII

# ---------------------------------------------------------------
Write-Host '[5/5] Adding to PATH...'
# ---------------------------------------------------------------
$p = [Environment]::GetEnvironmentVariable('Path', 'User')
$current = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + $p
$parts = $current -split ';' | Where-Object { $_ -ne '' }
if ($parts -notcontains $appDir) {
    [Environment]::SetEnvironmentVariable('Path', ($p.TrimEnd(';') + ';' + $appDir), 'User')
    Write-Host '   [OK] Added to PATH.'
} else {
    Write-Host '   [OK] Already in PATH.'
}

Remove-Item -Recurse -Force $tmpDir

Write-Host ''
Write-Host '============================================'
Write-Host '   INSTALLATION COMPLETE'
Write-Host '============================================'
Write-Host ''
Write-Host '   Open a NEW cmd window and type:'
Write-Host ''
Write-Host '       iainvisible'
Write-Host ''
Write-Host '   to launch the program.'
Write-Host '============================================'
Write-Host ''