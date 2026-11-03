# Build a one-dir Windows distribution. Run from the repository root:
#   powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1
$ErrorActionPreference = "Stop"

if (-not (Test-Path "pyproject.toml")) {
    throw "Run this script from the repository root."
}

uv run pyinstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name xray-detector `
    --collect-all PySide6 `
    --collect-all ultralytics `
    --collect-all rfdetr `
    --add-data "config;config" `
    --paths src `
    src/xray_detector/main.py

Write-Host ""
Write-Host "Build complete: dist/xray-detector"
Write-Host "Place datasets/models/config next to the executable or set app.data_root."
