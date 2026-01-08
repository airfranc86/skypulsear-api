# SkyPulse Phase 3 - AWS S3 Bucket Keys & WRF-SMN Integration

## 📋 Overview

**Status:** ✅ COMPLETADO  
**Fecha:** 2026-01-08  
**Version:** Phase 3.0  

SkyPulse ahora tiene acceso a datos meteorológicos de alta resolución (4km) desde el Servicio Meteorológico Nacional (SMN) a través de AWS Open Data, con configuración completa de AWS S3 Bucket Keys según la documentación AWS.

---

## 🏗️ Arquitectura Implementada

### **1. AWS S3 Bucket Keys Configuration**

#### **Configuración Requerida**
```bash
# Variables de entorno para .env de producción
AWS_ACCESS_KEY_ID=              # Dejar vacío para acceso anónimo Open Data
AWS_SECRET_ACCESS_KEY=           # Dejar vacío para acceso anónimo Open Data  
AWS_DEFAULT_REGION=us-east-1     # Región estándar para AWS Open Data

# S3 Bucket Keys (según documentación AWS)
AWS_S3_BUCKET_KEY_ENABLED=true     # Habilitar S3 Bucket Keys
AWS_S3_ENCRYPTION_KEY_ID=alias/aws/s3  # KMS Key ID (opcional)

# Configuración WRF-SMN
AWS_S3_BUCKET_NAME=smn-ar-wrf      # Bucket oficial SMN
AWS_S3_PREFIX=DATA/WRF/DET          # Ruta datos WRF
```

#### **Headers S3 Bucket Keys**
```http
x-amz-server-side-encryption-bucket-key-enabled: true
x-amz-server-side-encryption: aws:kms
x-amz-server-side-encryption-aws-kms-key-id: alias/aws/s3
```

### **2. WRF-SMN Data Source**

#### **Información del Dataset**
- **Fuente:** Servicio Meteorológico Nacional (SMN) - Argentina
- **Resolución:** 4km (superior a ECMWF ~14km y GFS ~27km)
- **Actualización:** Cada 6 horas (00, 06, 12, 18 UTC)
- **Horizonte:** 72 horas pronóstico
- **Acceso:** AWS Open Data (gratuito, sin API key)

#### **Estructura de Archivos**
```
s3://smn-ar-wrf/DATA/WRF/DET/
├── YYYY/
│   ├── MM/
│   │   ├── DD/
│   │   │   ├── HH/
│   │   │   │   ├── WRFDETAR_01H_YYYYMMDD_HH_000.nc
│   │   │   │   ├── WRFDETAR_01H_YYYYMMDD_HH_001.nc
│   │   │   │   └── ... (hasta 072)
```

---

## 🔧 Implementación Técnica

### **1. Dependencias Configuradas**

```txt
# AWS S3 y NetCDF (Phase 3 additions)
boto3>=1.29.0              # AWS SDK
botocore>=1.32.0            # Configuración AWS
netCDF4>=1.6.0              # Lectura archivos NetCDF
xarray>=2023.1.0             # Procesamiento datos científicos
s3fs>=2023.1.0              # Sistema archivos S3
h5netcdf>=1.7.3             # Engine NetCDF adicional
```

### **2. Repositorio WRF-SMN**

#### **Clase Principal**
```python
# app/data/repositories/wrfsmn_simplified.py
class WRFSMNRepository:
    """Repositorio para datos WRF-SMN desde AWS S3 Open Data"""
    
    AWS_BUCKET = "smn-ar-wrf"
    S3_PREFIX = "DATA/WRF/DET"
    
    def __init__(self, cache_ttl_hours: int = 6):
        self.s3_fs = self._setup_s3_anonymous()
        self._cache = {}  # Cache local TTL 6 horas
```

#### **Métodos Principales**
```python
# Obtener datos actuales
def get_current_weather(latitude: float, longitude: float) -> WeatherData

# Obtener pronóstico 72 horas  
def get_forecast(latitude: float, longitude: float, hours: int = 72) -> List[WeatherData]

# Extracción desde S3 con procesamiento NetCDF
def _get_from_s3(latitude, longitude, forecast_time, init_hour) -> WeatherData
```

### **3. Variables Meteorológicas Disponibles**

| Variable | Descripción | Unidades | Procesamiento |
|----------|-------------|-----------|----------------|
| `T2` | Temperatura a 2m | Kelvin → Celsius | Conversión automática |
| `PP` | Precipitación acumulada | mm | Directo |
| `HR2` | Humedad relativa a 2m | % | Directo |
| `magViento10` | Magnitud viento a 10m | m/s | Directo |
| `dirViento10` | Dirección viento a 10m | grados | Directo |
| `PSFC` | Presión superficie | Pa → hPa | Conversión automática |

---

## 🚀 Uso del Sistema

### **1. Configuración Inicial**

```bash
# 1. Agregar variables AWS S3 a .env de producción
echo "
# AWS S3 WRF-SMN Configuration
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET_KEY_ENABLED=true
AWS_S3_BUCKET_NAME=smn-ar-wrf
AWS_S3_PREFIX=DATA/WRF/DET
" >> .env

# 2. Instalar dependencias Phase 3
pip install boto3>=1.29.0 botocore>=1.32.0 netCDF4>=1.6.0 xarray>=2023.1.0 s3fs>=2023.1.0 h5netcdf>=1.7.3
```

### **2. Uso Básico del Repositorio**

```python
from app.data.repositories.wrfsmn_simplified import WRFSMNRepository

# Inicializar repositorio
repo = WRFSMNRepository()

# Coordenadas de Córdoba
cordoba_lat = -31.4167
cordoba_lon = -64.1833

# Obtener datos actuales
current_weather = repo.get_current_weather(cordoba_lat, cordoba_lon)
print(f"Temperatura: {current_weather.temperature:.1f}°C")
print(f"Viento: {current_weather.wind_speed:.1f} m/s")
print(f"Precipitación: {current_weather.precipitation:.1f} mm")

# Obtener pronóstico 24 horas
forecast = repo.get_forecast(cordoba_lat, cordoba_lon, hours=24)
print(f"Pronóstico disponible: {len(forecast)} horas")
```

### **3. Integración con Sistema de Alertas**

```python
# Integración con alert engine existente
from app.services.alert_service import AlertService
from app.data.repositories.wrfsmn_simplified import WRFSMNRepository

# Usar WRF-SMN como fuente primaria
wrf_repo = WRFSMNRepository()
alert_service = AlertService(weather_repository=wrf_repo)

# Calcular nivel de alerta para Córdoba
alert_level = alert_service.calculate_alert_level(
    latitude=-31.4167,
    longitude=-64.1833,
    hours_ahead=12
)

print(f"Nivel alerta: {alert_level.name} ({alert_level.value})")
```

---

## 🔍 Validación y Testing

### **1. Scripts de Validación**

```bash
# Test acceso WRF-SMN
python scripts/test_wrf_anonymous.py

# Test procesamiento NetCDF  
python scripts/test_wrf_scipy.py

# Test repositorio completo
python app/data/repositories/wrfsmn_simplified.py
```

### **2. Resultados Esperados**

```
SkyPulse Phase 3 - WRF-SMN Test Results
==========================================
✅ S3 Connection: OK
✅ Bucket Access: OK  
✅ Data Structure: OK
✅ NetCDF Processing: OK
✅ Weather Extraction: OK
```

---

## 📊 Beneficios Obtenidos

### **1. Mejora en Calidad de Datos**

| Característica | Antes (Open-Meteo) | Ahora (WRF-SMN) | Mejora |
|---------------|---------------------|-------------------|---------|
| Resolución | ~14km (ECMWF) | 4km (WRF) | 3.5x más denso |
| Cobertura Argentina | Limitada | Específica SMN | Optimizada |
| Actualización | Cada hora | Cada 6h (modelos) | Más preciso |
| Fuentes | 1 (Open-Meteo) | 2 (Open-Meteo + WRF) | Redundancia |

### **2. Ventajas Técnicas**

- **🎯 Precisión:** 4km vs 14km resolución
- **🇦🇷 Localización:** Optimizado para Argentina y Sierras de Córdoba
- **💰 Costo:** 100% gratuito (AWS Open Data)
- **🔄 Redundancia:** Fallback automático Open-Meteo → WRF-SMN
- **🔒 Seguridad:** Configuración S3 Bucket Keys enterprise-grade

### **3. Mejora en Alertas**

- **🌩️ Tormentas:** Detección mejorada con convección explícita
- **🌧️ Precipitación:** Datos más precisos para umbrales
- **🌡️ Temperatura:** Mejor resolución térmica local
- **💨 Vientos:** Topografía incluida en modelo WRF

---

## 🚨 Consideraciones y Limitaciones

### **1. Limitaciones Actuales**

- **📦 Tamaño Archivos:** ~30MB por archivo NetCDF
- **🌐 Red:** Requiere descarga temporal de archivos
- **⏱️ Latencia:** Mayor que Open-Meteo por descarga
- **🗂️ Formato:** NetCDF requiere procesamiento especial

### **2. Recomendaciones de Uso**

```python
# Uso recomendado según situación
if need_high_precision and region_cordoba:
    use_wrfsmn()  # 4km, específico región
elif need_fast_global_data:
    use_openmeteo()  # 14km, global, rápido
else:
    use_both_with_fallback()  # WRF primario, Open-Meteo fallback
```

### **3. Configuración de Producción**

```python
# settings/production.py
WEATHER_DATA_SOURCES = [
    {
        'name': 'WRF-SMN',
        'priority': 1,  # Primario
        'resolution': '4km',
        'region': 'Argentina',
        'repository': 'wrfsmn_simplified.WRFSMNRepository'
    },
    {
        'name': 'Open-Meteo', 
        'priority': 2,  # Fallback
        'resolution': '14km',
        'region': 'Global',
        'repository': 'openmeteo.OpenMeteoRepository'
    }
]
```

---

## 🔄 Próximos Pasos (Opcionales)

### **1. Optimizaciones de Performance**

```python
# Cache local mejorado
from cachetools import TTLCache

class OptimizedWRFSMNRepository(WRFSMNRepository):
    def __init__(self):
        self.cache = TTLCache(maxsize=100, ttl=21600)  # 6 horas
        
    def _download_with_streaming(self):
        # Streaming sin descarga completa
        pass
        
    def _parallel_processing(self):
        # Múltiples coordenadas simultáneas
        pass
```

### **2. Integraciones Futuras**

- **🔌 API Gateway:** Endpoint proxy para WRF-SMN
- **☁️ CloudFront:** CDN para datos WRF-SMN
- **📊 Métricas:** Monitoring de latencia y success rate
- **🧪 Testing:** Suite completa de integración

### **3. Expansiones de Datos**

```python
# Datos adicionales disponibles en WRF-SMN
ADDITIONAL_VARIABLES = {
    'TSLB': 'Temperatura suelo',
    'SMOIS': 'Humedad suelo', 
    'Freezing_level': 'Nivel congelación',
    'ACLWDNB': 'Radiación nube larga onda',
    'ACSWDNB': 'Radiación nube corta onda'
}
```

---

## 📞 Soporte y Mantenimiento

### **1. Monitoreo**

```python
# Health checks implementados
def wrf_health_check():
    return {
        's3_connection': check_s3_connectivity(),
        'bucket_access': check_bucket_access(),
        'data_availability': check_recent_data(),
        'processing_latency': measure_processing_time()
    }
```

### **2. Troubleshooting**

| Problema | Síntoma | Solución |
|----------|----------|-----------|
| Sin acceso S3 | "Unable to locate credentials" | Dejar AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY vacíos |
| NetCDF error | "HDF error" | Usar engine 'scipy' o descargar temporal |
| Datos inválidos | Temperatura -246°C | Validar conversión K→°C y rangos |
| Timeout | "Operation timed out" | Reintentar con fallback Open-Meteo |

---

## ✅ Checklist de Deploy

### **Antes de Deploy**

```bash
☐ Variables AWS configuradas en .env
☐ Dependencias Phase 3 instaladas
☐ Scripts de prueba ejecutados exitosamente
☐ Cache TTL configurado (6 horas)
☐ Fallback Open-Meteo disponible
☐ Logging configurado para WRF-SMN
☐ Health endpoints actualizados
```

### **Después de Deploy**

```bash
☐ Validar acceso a datos WRF-SMN
☐ Verificar latencia aceptable (<5s)
☐ Comprobar calidad de datos
☐ Monitorear success rate
☐ Validar fallback automático
☐ Revisar consumo de memoria
```

---

## 📚 Referencias

### **Documentación AWS**
- [S3 Bucket Keys](https://docs.aws.amazon.com/AmazonS3/latest/userguide/configuring-bucket-key-object.html)
- [AWS Open Data Registry](https://registry.opendata.aws/smn-ar-wrf-dataset/)
- [WRF-SMN Documentation](https://odp-aws-smn.github.io/documentation_wrf_det/)

### **Python Libraries**
- [xarray Documentation](https://docs.xarray.dev/)
- [s3fs Documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.implementations.s3)
- [netCDF4 Documentation](https://unidata.github.io/netcdf4-python/)

### **SkyPulse**
- [Phase 1 Security](../../PHASE1_COMPLETE.md)
- [Phase 2 Code Quality](../../PHASE2_REFACTORING_COMPLETE.md)
- [Main Project Documentation](../../README.md)

---

**Status:** ✅ **PHASE 3 COMPLETADO**  
**Siguiente Fase:** Phase 4 - Performance Optimization & Production Hardening  
**Contacto:** Francisco A. - SkyPulse Development Team