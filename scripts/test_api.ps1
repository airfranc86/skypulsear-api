# Script PowerShell para ejecutar tests de la API

Write-Host "🧪 Ejecutando tests de SkyPulse API..." -ForegroundColor Cyan

# Activar entorno virtual si existe
if (Test-Path ".venv") {
    Write-Host "📦 Activando entorno virtual..." -ForegroundColor Yellow
    & .\.venv\Scripts\Activate.ps1
}

# Instalar dependencias si es necesario
Write-Host "📦 Verificando dependencias..." -ForegroundColor Yellow
pip install -q -r requirements-dev.txt

# Ejecutar tests
Write-Host "🚀 Ejecutando tests..." -ForegroundColor Green
python -m pytest tests/ -v --tb=short

Write-Host "✅ Tests completados" -ForegroundColor Green

