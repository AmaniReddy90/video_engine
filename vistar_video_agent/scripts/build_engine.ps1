Write-Host "Building engine executable..."
$root = Split-Path -Parent $PSScriptRoot
$engineDir = Join-Path $root "engine"
Set-Location $engineDir
python -m pip install -r requirements.txt
pyinstaller -F -n vistar_engine -p . -m vistar_engine
Write-Host "Engine build complete."
