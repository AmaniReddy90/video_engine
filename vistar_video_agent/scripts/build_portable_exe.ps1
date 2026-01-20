Write-Host "Building portable Vistar Video Agent..."
$root = Split-Path -Parent $PSScriptRoot
$engineDir = Join-Path $root "engine"
$appDir = Join-Path $root "app"
$resourcesDir = Join-Path $root "resources"
$distDir = Join-Path $root "dist_release"

if (!(Test-Path $distDir)) { New-Item -ItemType Directory -Path $distDir | Out-Null }

Write-Host "Building engine..."
& "$PSScriptRoot\build_engine.ps1"

Write-Host "Copying resources..."
if (!(Test-Path $resourcesDir)) { New-Item -ItemType Directory -Path $resourcesDir | Out-Null }
Copy-Item -Path "$engineDir\dist\vistar_engine.exe" -Destination "$resourcesDir\engine" -Force

Write-Host "Building Tauri app..."
Set-Location $appDir
npm install
npm run tauri build

Write-Host "Collecting artifacts..."
Copy-Item -Path "$appDir\src-tauri\target\release\*.exe" -Destination $distDir -Force
Copy-Item -Path $resourcesDir -Destination $distDir -Recurse -Force
Copy-Item -Path (Join-Path $root "vault") -Destination $distDir -Recurse -Force

$portableDir = Join-Path $distDir "portable"
if (Test-Path $portableDir) { Remove-Item $portableDir -Recurse -Force }
New-Item -ItemType Directory -Path $portableDir | Out-Null
Copy-Item -Path $distDir\*.exe -Destination $portableDir -Force
Copy-Item -Path $resourcesDir -Destination $portableDir -Recurse -Force
Copy-Item -Path (Join-Path $root "vault") -Destination $portableDir -Recurse -Force
Copy-Item -Path (Join-Path $root "README_RUN.txt") -Destination $portableDir -Force

Compress-Archive -Path $portableDir\* -DestinationPath (Join-Path $distDir "portable.zip") -Force
Write-Host "Portable build complete."
