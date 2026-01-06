#!/usr/bin/env python3
"""
Script para extraer API keys del .env local y mostrarlas para copiar a Render.

NO muestra los valores completos por seguridad, solo indica si están configuradas.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env desde app/
env_path = Path(__file__).parent.parent / "app" / ".env"

if not env_path.exists():
    print(f"❌ Archivo .env no encontrado en: {env_path}")
    print(f"   Buscando en: {env_path.absolute()}")
    exit(1)

load_dotenv(env_path)

# Variables que necesitamos verificar
required_vars = {
    "WINDY_POINT_FORECAST_API_KEY": "Requerido - Para Windy-GFS (recomendado para Argentina)",
    "METEOSOURCE_API_KEY": "Opcional - Para alertas y datos adicionales",
}

print("=" * 70)
print("API KEYS EN .ENV LOCAL")
print("=" * 70)
print()

for var_name, description in required_vars.items():
    value = os.getenv(var_name)
    if value:
        # Mostrar solo primeros y últimos 4 caracteres por seguridad
        masked = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
        print(f"✅ {var_name}")
        print(f"   {description}")
        print(f"   Valor: {masked} ({len(value)} caracteres)")
        print()
    else:
        print(f"❌ {var_name}")
        print(f"   {description}")
        print(f"   ⚠️  NO CONFIGURADA")
        print()

print("=" * 70)
print("INSTRUCCIONES PARA COPIAR A RENDER:")
print("=" * 70)
print()
print("1. Ir a Render Dashboard: https://dashboard.render.com")
print("2. Seleccionar servicio: skypulse-api")
print("3. Ir a pestaña 'Environment'")
print("4. Para cada variable marcada con ✅:")
print("   - Click en 'Add Environment Variable'")
print("   - Key: (nombre de la variable)")
print("   - Value: (copiar valor completo del .env)")
print("   - Click 'Save Changes'")
print()
print("5. Después de agregar todas, hacer 'Manual Deploy'")
print()
print("📖 Ver guía completa en: Reportes/COPIAR_API_KEYS_A_RENDER.md")
print()
