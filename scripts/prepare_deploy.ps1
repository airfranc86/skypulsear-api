# Script PowerShell para preparar commit y push para despliegue en Render
# Repositorio: https://github.com/airfranc86/skypulsear-api

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "SkyPulse v2.0.0 - Preparacion para Deploy" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "render.yaml")) {
    Write-Host "ERROR: No se encuentra render.yaml. Ejecutar desde el directorio raiz del proyecto." -ForegroundColor Red
    exit 1
}

Write-Host "[*] Verificando estado de Git..." -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "[*] Archivos a agregar:" -ForegroundColor Yellow
Write-Host "  - render.yaml (build command actualizado)"
Write-Host "  - requirements.txt (prometheus-client)"
Write-Host "  - app/ (todos los cambios)"
Write-Host "  - tests/ (nuevos tests)"
Write-Host "  - docs/ (documentacion)"
Write-Host "  - scripts/ (scripts de utilidad)"
Write-Host ""

$confirm = Read-Host "¿Continuar con el commit? (y/n)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Cancelado." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "[*] Agregando archivos..." -ForegroundColor Yellow

# Agregar archivos modificados y nuevos
git add render.yaml
git add requirements.txt
git add app/
git add tests/
git add docs/
git add scripts/
git add CHANGELOG_v2.0.0.md

# Verificar que no se agreguen archivos sensibles
$sensitive = git status --short | Select-String -Pattern "\.env|secrets|keys"
if ($sensitive) {
    Write-Host "ERROR: Se detectaron archivos sensibles. Revisar antes de commit." -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Archivos agregados" -ForegroundColor Green
Write-Host ""

Write-Host "[*] Creando commit..." -ForegroundColor Yellow

$commitMessage = @"
feat: SkyPulse v2.0.0 - Logging estructurado, circuit breakers, métricas y retry logic

- Implementado logging estructurado JSON con correlation IDs
- Agregados circuit breakers para Meteosource y Windy
- Centralizado retry logic con decoradores reutilizables
- Implementadas métricas Prometheus en endpoint /metrics
- Exception handlers globales con respuestas consistentes
- Fix: build command para netCDF4 en Render (numpy antes de netCDF4)
- CORS actualizado con dominio de Vercel (skypulse-ar.vercel.app)
- Tests: circuit breaker (88%), retry (91%), metrics (91%)
- Documentación completa de despliegue y troubleshooting

Breaking Changes: Ninguno (compatible con v1.x)
Nuevas Dependencias: prometheus-client>=0.19.0
"@

git commit -m $commitMessage

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Commit creado exitosamente" -ForegroundColor Green
    Write-Host ""
    Write-Host "[*] Para hacer push, ejecutar:" -ForegroundColor Yellow
    Write-Host "    git push origin main"
    Write-Host "    (o 'git push origin master' si tu branch es master)"
    Write-Host ""
    $pushConfirm = Read-Host "¿Hacer push ahora? (y/n)"
    if ($pushConfirm -eq "y" -or $pushConfirm -eq "Y") {
        Write-Host "[*] Haciendo push..." -ForegroundColor Yellow
        git push origin main
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Push completado. Render comenzará el deploy automáticamente." -ForegroundColor Green
            Write-Host ""
            Write-Host "Próximos pasos:" -ForegroundColor Cyan
            Write-Host "1. Monitorear deploy en Render Dashboard"
            Write-Host "2. Verificar health check: curl https://tu-api.onrender.com/health"
            Write-Host "3. Verificar logs en Render Dashboard"
        } else {
            Write-Host "[ERROR] Push falló. Verificar configuración de Git." -ForegroundColor Red
        }
    }
} else {
    Write-Host "[ERROR] Fallo al crear commit" -ForegroundColor Red
    exit 1
}

