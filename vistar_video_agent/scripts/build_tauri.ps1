Write-Host "Building Tauri desktop shell..."
$root = Split-Path -Parent $PSScriptRoot
$appDir = Join-Path $root "app"
Set-Location $appDir
npm install
npm run tauri build
Write-Host "Tauri build complete."
