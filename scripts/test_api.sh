#!/bin/bash
# Script para ejecutar tests de la API

echo "🧪 Ejecutando tests de SkyPulse API..."

# Activar entorno virtual si existe
if [ -d ".venv" ]; then
    source .venv/bin/activate  # Linux/Mac
    # En Windows: .venv\Scripts\activate
fi

# Instalar dependencias si es necesario
echo "📦 Verificando dependencias..."
pip install -q -r requirements-dev.txt

# Ejecutar tests
echo "🚀 Ejecutando tests..."
pytest tests/ -v --tb=short

echo "✅ Tests completados"

