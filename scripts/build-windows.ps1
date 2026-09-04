param([string]$Python = 'python', [switch]$PortableOnly)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& $Python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& $Python -m PyInstaller --noconfirm --clean --onedir --name Lantern --add-data 'lantern/ui;lantern/ui' run.py
if ($LASTEXITCODE -ne 0) { throw 'Application build failed' }
if (-not $PortableOnly) {
    $compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if (-not $compiler) { throw 'Install Inno Setup 6 and put ISCC.exe on PATH, or use -PortableOnly.' }
    & $compiler.Source packaging\windows.iss
    if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
}
