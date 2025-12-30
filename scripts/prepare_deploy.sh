#!/bin/bash
# Script para preparar commit y push para despliegue en Render
# Repositorio: https://github.com/airfranc86/skypulsear-api

echo "=========================================="
echo "SkyPulse v2.0.0 - Preparacion para Deploy"
echo "=========================================="
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "render.yaml" ]; then
    echo "ERROR: No se encuentra render.yaml. Ejecutar desde el directorio raiz del proyecto."
    exit 1
fi

echo "[*] Verificando estado de Git..."
git status

echo ""
echo "[*] Archivos a agregar:"
echo "  - render.yaml (build command actualizado)"
echo "  - requirements.txt (prometheus-client)"
echo "  - app/ (todos los cambios)"
echo "  - tests/ (nuevos tests)"
echo "  - docs/ (documentacion)"
echo "  - scripts/ (scripts de utilidad)"
echo ""

read -p "¿Continuar con el commit? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelado."
    exit 1
fi

echo ""
echo "[*] Agregando archivos..."

# Agregar archivos modificados y nuevos
git add render.yaml
git add requirements.txt
git add app/
git add tests/
git add docs/
git add scripts/
git add CHANGELOG_v2.0.0.md

# Verificar que no se agreguen archivos sensibles
if git status --short | grep -E "\.env|secrets|keys"; then
    echo "ERROR: Se detectaron archivos sensibles. Revisar antes de commit."
    exit 1
fi

echo "[OK] Archivos agregados"
echo ""

echo "[*] Creando commit..."
git commit -m "feat: SkyPulse v2.0.0 - Logging estructurado, circuit breakers, métricas y retry logic

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
Nuevas Dependencias: prometheus-client>=0.19.0"

if [ $? -eq 0 ]; then
    echo "[OK] Commit creado exitosamente"
    echo ""
    echo "[*] Para hacer push, ejecutar:"
    echo "    git push origin main"
    echo "    (o 'git push origin master' si tu branch es master)"
    echo ""
    read -p "¿Hacer push ahora? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "[*] Haciendo push..."
        git push origin main || git push origin master
        if [ $? -eq 0 ]; then
            echo "[OK] Push completado. Render comenzará el deploy automáticamente."
            echo ""
            echo "Próximos pasos:"
            echo "1. Monitorear deploy en Render Dashboard"
            echo "2. Verificar health check: curl https://tu-api.onrender.com/health"
            echo "3. Verificar logs en Render Dashboard"
        else
            echo "[ERROR] Push falló. Verificar configuración de Git."
        fi
    fi
else
    echo "[ERROR] Fallo al crear commit"
    exit 1
fi

