#!/usr/bin/env python3
"""
Script de prueba para verificar acceso a WRF-SMN desde AWS S3.

Uso:
    python scripts/test_wrf_smn.py

Este script prueba:
1. Instalación de dependencias (netCDF4, xarray, s3fs)
2. Acceso anónimo a AWS S3 bucket smn-ar-wrf
3. Lectura de archivo NetCDF de ejemplo
4. Extracción de variables meteorológicas
5. Integración con WRFSMNRepository
"""

import sys
import os
from datetime import UTC, datetime, timedelta

# Agregar raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_dependencies():
    """Verificar que las dependencias estén instaladas."""
    print("=" * 60)
    print("1. Verificando dependencias...")
    print("=" * 60)

    dependencies = {
        "s3fs": "s3fs",
        "xarray": "xarray",
        "netCDF4": "netCDF4",
        "numpy": "numpy",
    }

    missing = []
    for name, module in dependencies.items():
        try:
            __import__(module)
            print(f"  ✅ {name} instalado")
        except ImportError:
            print(f"  ❌ {name} NO instalado")
            missing.append(name)

    if missing:
        print(f"\n⚠️  Faltan dependencias: {', '.join(missing)}")
        print("   Instalar con: pip install -r requirements.txt")
        return False

    print("\n✅ Todas las dependencias están instaladas\n")
    return True


def test_s3_access():
    """Probar acceso anónimo a S3."""
    print("=" * 60)
    print("2. Probando acceso anónimo a AWS S3...")
    print("=" * 60)

    try:
        import s3fs

        # Configurar acceso anónimo
        fs = s3fs.S3FileSystem(anon=True)
        print("  ✅ S3FileSystem configurado para acceso anónimo")

        # Probar acceso al bucket
        bucket = "smn-ar-wrf"
        bucket_path = f"s3://{bucket}/"

        if fs.exists(bucket_path):
            print(f"  ✅ Bucket '{bucket}' es accesible")
        else:
            print(f"  ⚠️  No se pudo verificar existencia del bucket (puede ser normal)")

        return True, fs

    except Exception as e:
        print(f"  ❌ Error accediendo a S3: {e}")
        return False, None


def test_netcdf_structure(fs):
    """Probar lectura de estructura de archivo NetCDF."""
    print("=" * 60)
    print("3. Probando lectura de archivo NetCDF de ejemplo...")
    print("=" * 60)

    try:
        import xarray as xr

        # Construir ruta a un archivo reciente
        # WRF-SMN se actualiza 4 veces al día (00, 06, 12, 18 UTC)
        now = datetime.now(UTC)
        init_hour = (now.hour // 6) * 6  # Redondear a 00, 06, 12, 18

        # Intentar con la inicialización más reciente
        init_date = now.replace(hour=init_hour, minute=0, second=0, microsecond=0)
        date_str = init_date.strftime("%Y/%m/%d/%H")
        filename = f"WRFDETAR_01H_{init_date.strftime('%Y%m%d')}_{init_hour:02d}_000.nc"
        s3_key = f"DATA/WRF/DET/{date_str}/{filename}"
        s3_path = f"s3://smn-ar-wrf/{s3_key}"

        print(f"  Intentando leer: {s3_path}")

        if not fs.exists(s3_path):
            # Intentar con una hora anterior
            init_date = init_date - timedelta(hours=6)
            date_str = init_date.strftime("%Y/%m/%d/%H")
            filename = f"WRFDETAR_01H_{init_date.strftime('%Y%m%d')}_{init_date.hour:02d}_000.nc"
            s3_key = f"DATA/WRF/DET/{date_str}/{filename}"
            s3_path = f"s3://smn-ar-wrf/{s3_key}"
            print(f"  Archivo no encontrado, intentando: {s3_path}")

        if not fs.exists(s3_path):
            print(f"  ⚠️  Archivo no encontrado (puede que aún no esté disponible)")
            print(f"     WRF-SMN se actualiza en: 00, 06, 12, 18 UTC")
            return False

        print(f"  ✅ Archivo encontrado: {s3_path}")

        # Abrir dataset
        with fs.open(s3_path, mode="rb") as f:
            ds = xr.open_dataset(f, decode_times=True)

            print(f"\n  📊 Información del dataset:")
            print(f"     Dimensiones: {dict(ds.dims)}")
            print(f"     Variables: {len(ds.data_vars)} variables")
            print(f"     Coordenadas: {list(ds.coords.keys())}")

            # Verificar variables esperadas
            expected_vars = ["T2", "RH2", "U10", "V10", "PSFC", "RAINC", "RAINNC"]
            found_vars = []
            missing_vars = []

            for var in expected_vars:
                if var in ds.data_vars:
                    found_vars.append(var)
                else:
                    missing_vars.append(var)

            print(f"\n  ✅ Variables encontradas: {', '.join(found_vars)}")
            if missing_vars:
                print(f"  ⚠️  Variables no encontradas: {', '.join(missing_vars)}")

            ds.close()
            return True

    except Exception as e:
        print(f"  ❌ Error leyendo NetCDF: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_repository():
    """Probar WRFSMNRepository."""
    print("=" * 60)
    print("4. Probando WRFSMNRepository...")
    print("=" * 60)

    try:
        from app.data.repositories.wrfsmn_repository import WRFSMNRepository

        # Crear repositorio
        repo = WRFSMNRepository(use_meteosource_fallback=False)
        print("  ✅ WRFSMNRepository creado")

        # Probar obtener datos actuales (Córdoba, Argentina)
        lat = -31.4201
        lon = -64.1888

        print(f"\n  Probando obtener datos para ({lat}, {lon})...")
        weather_data = repo.get_current_weather(lat, lon)

        if weather_data:
            print(f"  ✅ Datos obtenidos:")
            print(f"     Temperatura: {weather_data.temperature}°C")
            print(f"     Humedad: {weather_data.humidity}%")
            print(f"     Viento: {weather_data.wind_speed} m/s")
            print(f"     Precipitación: {weather_data.precipitation} mm")
            print(f"     Fuente: {weather_data.source}")
            return True
        else:
            print(
                f"  ⚠️  No se pudieron obtener datos (puede ser normal si el archivo no está disponible)"
            )
            return False

    except Exception as e:
        print(f"  ❌ Error probando repositorio: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_storm_risk_integration():
    """Probar integración con cálculo de storm_risk."""
    print("=" * 60)
    print("5. Probando integración con cálculo de storm_risk...")
    print("=" * 60)

    try:
        from app.services.risk_scoring import RiskScoringService
        from app.data.schemas.normalized_weather import UnifiedForecast, WeatherSource
        from datetime import UTC

        # Crear forecast simulado con WRF-SMN
        forecast = UnifiedForecast(
            latitude=-31.4201,
            longitude=-64.1888,
            timestamp=datetime.now(UTC),
            temperature_celsius=25.0,
            humidity_pct=75.0,
            wind_speed_ms=15.0,
            wind_direction_deg=180.0,
            precipitation_mm=12.0,  # Precipitación alta (indica tormenta)
            pressure_hpa=1013.0,
            sources_used=[WeatherSource.WRF_SMN],
        )

        # Crear servicio de risk scoring
        service = RiskScoringService()

        # Calcular storm risk
        storm_risk = service._calculate_storm_risk([forecast])

        print(f"  ✅ Storm risk calculado: {storm_risk}")

        if storm_risk > 0:
            print(f"     ⚠️  Riesgo de tormenta detectado (esperado con precip=12mm)")
        else:
            print(f"     ℹ️  Sin riesgo de tormenta")

        return True

    except Exception as e:
        print(f"  ❌ Error probando integración: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Ejecutar todas las pruebas."""
    print("\n" + "=" * 60)
    print("PRUEBAS DE WRF-SMN - AWS S3")
    print("=" * 60 + "\n")

    results = []

    # 1. Verificar dependencias
    if not test_dependencies():
        print("\n❌ Faltan dependencias. Instalar con: pip install -r requirements.txt")
        sys.exit(1)

    # 2. Probar acceso S3
    s3_ok, fs = test_s3_access()
    results.append(("Acceso S3", s3_ok))

    if not s3_ok:
        print("\n❌ No se pudo acceder a S3. Verificar conectividad.")
        sys.exit(1)

    # 3. Probar lectura NetCDF
    netcdf_ok = test_netcdf_structure(fs)
    results.append(("Lectura NetCDF", netcdf_ok))

    # 4. Probar repositorio
    repo_ok = test_repository()
    results.append(("WRFSMNRepository", repo_ok))

    # 5. Probar integración storm_risk
    integration_ok = test_storm_risk_integration()
    results.append(("Integración storm_risk", integration_ok))

    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n✅ Todas las pruebas pasaron. WRF-SMN está listo para usar en Render.")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisar errores arriba.")

    print("\n" + "=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
