# Auditoría: Modelos predictivos y estado real del sistema SkyPulse
Fecha: 2026-02-15

**Rol:** Arquitecto senior sistemas predictivos / MLOps, meteorología computacional.  
**Alcance:** Código del repositorio + documentación técnica pública (web).  
**Evidencia:** Referencias exactas a archivos y líneas.

---

## Fuentes de predicción (documentación de referencia)

Las predicciones del servicio provienen de:

- **Windy (modelo GFS):** API Point Forecast de Windy. En este proyecto se usa únicamente el **modelo GFS** (Global Forecast System), que es el plan gratuito/accesible vía API key. No se usan ECMWF ni ICON en producción.
- **WRF-SMN (datos SMN):** Salidas del modelo WRF del Servicio Meteorológico Nacional, publicadas en AWS Open Data (bucket `smn-ar-wrf`). Se **ingieren datos ya generados**; el modelo WRF **no se ejecuta** en este servicio.

---

## 1. Modelos realmente implementados

### 1.1 Fuentes de datos (no modelos estadísticos ni ML)

| Componente | Tipo | Evidencia | Estado |
|------------|------|-----------|--------|
| **Windy Point Forecast API (GFS)** | API externa (modelo GFS vía Windy) | `windy_repository.py`: `base_url = "https://api.windy.com/api/point-forecast/v2"`, `get_current_weather()`, `get_forecast()` con `requests.post()` | **Activo** si `WINDY_POINT_FORECAST_API_KEY` está configurado |
| **WRF-SMN (ingesta desde AWS S3)** | Lectura de NetCDF precomputados (no ejecución WRF) | `wrfsmn_repository.py`: bucket `smn-ar-wrf`, `s3fs.S3FileSystem(anon=True)`, `xr.open_dataset()`, `_extract_weather_from_netcdf()` | **Activo** si `boto3`, `s3fs`, `xarray`, `netCDF4` se importan sin error (`WRFSMN_AVAILABLE=True`) |
| **UnifiedWeatherEngine** | Orquestador (fusión de fuentes) | `unified_weather_engine.py`: `_fetch_all_sources()`, `_fetch_forecast_safe()`, fusión por pesos. Sin entrenamiento ni artefactos ML | **Activo** |
| **PatternDetector** | Reglas por umbrales (no ML) | `pattern_detector.py`: `THRESHOLDS` (CAPE, wind_gust, precip, heat_wave_day, etc.), `detect_patterns(forecasts)` comparando con umbrales | **Activo** |
| **RiskScoringService** | Reglas por perfil (no ML) | `risk_scoring.py`: pesos por perfil (PILOT, FARMER, etc.), `_score_to_category()`, sin `fit()` ni `.predict()` | **Activo** |
| **AlertService** | Reglas sobre patrones (no ML) | `alert_service.py`: genera alertas a partir de `DetectedPattern` y `UnifiedForecast` | **Activo** |

**No hay en el código:** ARIMA, SARIMA, Prophet, RandomForest, XGBoost, LSTM, sklearn, statsmodels, tensorflow, torch.  
**Verificación:** `grep -r "ARIMA\|Prophet\|sklearn\|\.fit(\|\.predict(" apps/api/app` → solo `verification.py` usa "predicted" como salida de un modelo numérico (Windy/WRF-SMN) para métricas MAE/RMSE, no como modelo ML.

### 1.2 WRF: no se ejecuta en este sistema

- **WRF** no se corre en la aplicación.  
- Se **leen salidas ya generadas** por el SMN en AWS Open Data: bucket `smn-ar-wrf`, formato NetCDF (`WRFDETAR_01H_*`).  
- Referencia: `wrfsmn_repository.py` L38-50, L293-309; documentación SMN: https://registry.opendata.aws/smn-ar-wrf-dataset/

---

## 2. Modelos declarados pero no funcionales o no usados

| Elemento | Dónde se declara | Por qué no está operativo |
|----------|------------------|----------------------------|
| **Windy-ECMWF** | `unified_weather_engine._get_available_sources()` devuelve `"windy_ecmwf"`; `repository_factory.source_map` tiene `"windy_ecmwf" → "Windy-ECMWF"` | Factory solo crea **Windy-GFS** (`create_all_available_repositories()` L121-126). No existe `repositories["Windy-ECMWF"]` → `get_repository("windy_ecmwf")` devuelve `None` |
| **Windy-ICON** | Mismo mapeo en `source_map` y en normalizer/fusion | No se instancia ningún repo "Windy-ICON" |
| **Endpoints /weather/current y /weather/forecast** | `weather.py` L28-56 (current), L62-98 (forecast) | Devuelven **mock fijo** (ej. `temperature: 22.5`, `conditions: "partly cloudy"`). No llaman a `UnifiedWeatherEngine` ni a repositorios |
| **ModelComparisonService** | `model_comparison.py` y `unified_weather_engine.get_model_comparison()` | No hay router que exponga `get_model_comparison()`. Solo uso interno, sin endpoint HTTP |
| **Verification (MAE, RMSE, Bias)** | `verification.py` | Funciones de comparación observado vs predicho; ningún endpoint las expone en la API |
| **secure_weather** | `secure_weather.py` | Referencia a `current_user` no inyectada en el snippet; no está incluido en `main.py` como router (solo `weather`, `risk`, `alerts`, `patterns`) |

---

## 3. Estado real del sistema

### 3.1 Flujo que sí usa datos reales

- **Risk:** `risk.py` → `UnifiedWeatherEngine().get_unified_forecast()` → `_fetch_all_sources()` → Windy-GFS + WRF-SMN (si está disponible). Luego PatternDetector, AlertService, RiskScoringService.  
- **Alerts:** `alerts.py` → mismo `get_unified_forecast()` + PatternDetector + AlertService.  
- **Patterns:** `patterns.py` → mismo `get_unified_forecast()` + PatternDetector.

### 3.2 Flujo que no usa modelos (mock)

- **GET /api/v1/weather/current** y **GET /api/v1/weather/forecast** → respuestas hardcodeadas en `weather.py`. No hay inferencia ni llamada a Windy/WRF-SMN.

### 3.3 Qué genera las “predicciones” actuales

- **Predicciones operativas** (risk, alertas, patrones): **Windy-GFS** (API) y, si el entorno carga `WRFSMNRepository`, **WRF-SMN** (lectura S3).  
- **Tiempos de inferencia:** Dominados por: (1) HTTP a Windy (~1–5 s), (2) lectura S3 + xarray NetCDF para WRF-SMN (segundos por archivo, según latencia y tamaño). Timeouts recientes: 8 s por fuente en `unified_weather_engine` (`future.result(timeout=8)`).  
- **Cuellos de botella:** Una fuente lenta (p. ej. S3/NetCDF) bloqueaba hasta 30 s; se mitigó con timeout por fuente. Render free: cold start y memoria pueden afectar carga de xarray/netCDF4.

### 3.4 Configuraciones inconsistentes

- **weather router:** Documentación y frontend sugieren “weather desde la API”; en código es mock.  
- **WRFSMNRepository `__init__`:** Doble bloque try/except (L66-106 y L107-141); el segundo sobrescribe `self.s3_fs`. Código redundante y posible bug si el primero falla y el segundo usa credenciales por defecto.  
- **UnifiedWeatherEngine** pide `windy_ecmwf` y `windy_gfs`; solo `windy_gfs` tiene repo creado → `windy_ecmwf` siempre retorna `None` en cada llamada.

---

## 4. Riesgos críticos

1. **Endpoints /weather/current y /weather/forecast son mock:** Los usuarios y el front pueden creer que ven datos en vivo; en realidad son valores fijos.  
2. **WRF-SMN depende de imports pesados:** Si en Render (u otro host) falla la instalación de `boto3`, `s3fs`, `xarray`, `netCDF4`, `WRFSMN_AVAILABLE=False` y solo queda Windy-GFS.  
3. **Deuda en wrfsmn_repository:** Doble configuración de S3 y `except Exception` duplicado dificultan mantenimiento y diagnóstico.  
4. **Sin modelos ML ni estadísticos:** No hay reentrenamiento, versionado de modelos ni pipeline MLOps; el sistema es reglas + ingestas externas.  
5. **ModelComparisonService y Verification no expuestos:** Capacidad de comparar modelos y métricas existe en código pero no en API.

---

## 5. Investigación de opciones gratuitas en Argentina (documentación pública)

### 5.1 WRF en AWS (ejecutar uno mismo)

- **Free tier:** Insuficiente para ejecutar WRF (almacenamiento y cómputo de inputs/salidas típicos superan límites).  
- **Alternativas en AWS:** WRF Cloud (cuenta propia), ParallelCluster, instancias HPC (p. ej. Hpc6a) — todas por encima de free tier y con costo.  
- **Conclusión:** Ejecutar WRF en AWS no es viable en plan gratuito; lo viable es **consumir datos ya publicados** (p. ej. SMN en S3).

### 5.2 Datos WRF-SMN (Argentina) – ya usado en el código

- **SMN en AWS Open Data:** Bucket `smn-ar-wrf`, región `us-west-2`, acceso anónimo, sin cuenta AWS.  
- WRF 4.0, 4 km, 4 inicializaciones/día (00, 06, 12, 18 UTC), lead time 72 h.  
- Documentación: https://registry.opendata.aws/smn-ar-wrf-dataset/ y https://odp-aws-smn.github.io/documentation_wrf_det  
- **Conclusión:** Es la opción gratuita y legal para “WRF” en Argentina; el código ya la usa (solo ingesta, no ejecución).

### 5.3 Ejecutar WRF en otros entornos (referencias públicas)

- **Google Cloud / HPC:** Codelabs y guías para WRF en GCP con Slurm; requieren cuotas (p. ej. 480 vCPUs, 500 GB disco) y no son free tier.  
- **Colab:** No hay soporte directo para WRF; sería muy limitado por CPU/memoria y tiempo de sesión.  
- **HPC universitario (Argentina):** Posible en centros con WRF instalado (p. ej. MinCyT, universidades); no hay API estándar; acceso por convenios.  
- **Docker local:** Imágenes WRF existen; ejecución seria requiere muchos núcleos y RAM; útil para I+D, no para servicio 24/7 gratuito.

### 5.4 Alternativas de datos numéricos gratuitos (sin ejecutar WRF)

- **Open-Meteo:** Ofrece **GFS** vía API gratuita (sin API key para uso no comercial), global, hasta ~16 días.  
- Documentación: https://open-meteo.com/en/docs/gfs-api  
- **Conclusión:** Alternativa gratuita a Windy para GFS; se puede usar como fuente adicional o respaldo sin coste de API key.

---

## 6. Alternativa viable a “AWS + ejecutar WRF”

- **No es necesario “reemplazar WRF”** ejecutándolo uno mismo: el sistema ya usa **salidas WRF-SMN** desde AWS Open Data (solo lectura).  
- **Si la ingesta S3/NetCDF es inestable o pesada** (p. ej. en Render):

  **Opción A – Mantener WRF-SMN como está:**  
  Corregir `wrfsmn_repository.__init__` (un solo camino de configuración S3, anónimo por defecto), mantener timeouts y fallback a score por defecto cuando no hay datos (ya implementado en risk).

  **Opción B – Añadir Open-Meteo GFS como fuente:**  
  Implementar un repo “Open-Meteo” que consuma la API GFS (gratuita). Daría una segunda fuente numérica sin API key y reduciría dependencia de Windy cuando falle o rate-limit.

  **Opción C – Simplificar a solo Windy (o solo Open-Meteo):**  
  Si se quiere mínima complejidad, usar solo una fuente (p. ej. Windy-GFS o Open-Meteo GFS) y quitar WRF-SMN en entornos donde boto3/xarray den problemas. La fusión multi-modelo pasaría a un solo modelo.

- **No se recomienda** intentar “ejecutar WRF” en Render/Colab/free tier; sí consumir datos ya publicados (SMN S3 o APIs como Open-Meteo).

---

## 7. Plan inmediato de ejecución (máx. 7 pasos concretos)

1. **Conectar /weather/current y /weather/forecast a datos reales**  
   - En `weather.py`, reemplazar el mock por: instanciar `UnifiedWeatherEngine()`, llamar `get_current_unified()` para current y `get_unified_forecast()` para forecast (con parámetros `lat`, `lon`, `hours`/días según contrato actual).  
   - Mapear la respuesta normalizada al formato JSON que ya consume el frontend.  
   - Mantener `require_api_key` y manejo de errores (ej. 503 si no hay datos).

2. **Corregir `wrfsmn_repository.__init__`**  
   - Un solo flujo: por defecto solo acceso anónimo S3 (`s3fs.S3FileSystem(anon=True)`), sin doble try/except ni sobrescritura de `self.s3_fs`.  
   - Opcional: si existen `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY`, usar credenciales; si no, anónimo.  
   - Eliminar el `except Exception` duplicado (L104-106) y el bloque redundante que pueda dejar `s3_fs` en estado inconsistente.

3. **Opcional: añadir Open-Meteo GFS como fuente**  
   - Crear `open_meteo_repository.py` (o similar) que llame a la API GFS de Open-Meteo (sin API key).  
   - Implementar `get_current_weather()` y `get_forecast()` devolviendo el mismo tipo que los otros repos (o adaptar normalizer).  
   - En `repository_factory` y en `UnifiedWeatherEngine._get_available_sources()` registrar la nueva fuente para que la fusión pueda usar GFS vía Open-Meteo además de Windy/WRF-SMN.

4. **Estabilizar comportamiento cuando no hay datos**  
   - En `alerts.py` y `patterns.py`: si `get_unified_forecast()` devuelve lista vacía, no devolver 503; devolver 200 con listas vacías de alertas/patrones y un mensaje tipo “Datos no disponibles” (igual que en risk con score por defecto).  
   - Así se evita 503 en cascada cuando S3 o Windy fallan.

5. **Documentar estado real de fuentes**  
   - En README o docs: “Predicciones provienen de **Windy (modelo GFS, el gratuito)** y/o **WRF-SMN** (datos del SMN en S3). El modelo WRF **no se ejecuta** en este servicio; solo se consumen sus salidas ya publicadas.”  
   - Indicar que /weather/current y /weather/forecast, tras el paso 1, usarán esas mismas fuentes.

6. **Verificar Render**  
   - Confirmar que en el entorno de Render están instalados `boto3`, `s3fs`, `xarray`, `netCDF4` (según `requirements.txt`) y que no hay fallo de import de `WRFSMNRepository`.  
   - Si la memoria o el cold start son un problema, valorar desactivar WRF-SMN en Render (variable o flag) y dejar solo Windy o Windy + Open-Meteo.

7. **Opcional: exponer comparación y métricas**  
   - Añadir endpoint (p. ej. GET /api/v1/models/compare o /api/v1/verification) que use `UnifiedWeatherEngine.get_model_comparison()` y/o `verification.calculate_metrics()` con datos observados si en el futuro se tienen estaciones; si no hay observaciones, posponer o documentar como “solo para uso interno”.

---

**Resumen ejecutivo**

- **Implementados y en uso:** **Windy (modelo GFS, el gratuito)** vía API Point Forecast, ingesta WRF-SMN (datos SMN en S3), fusión + reglas (patrones, riesgo, alertas).  
- **Declarados pero no funcionales:** Windy-ECMWF/ICON (solo GFS está activo), endpoints /weather en modo mock, comparación/verificación sin API.  
- **WRF:** No se ejecuta en el servicio; solo se consumen datos WRF-SMN ya publicados en AWS.  
- **Opción gratuita en Argentina:** Seguir usando SMN en S3; añadir Open-Meteo GFS si se quiere una segunda fuente sin costo.  
- **Acción inmediata:** Conectar weather a datos reales, corregir init de WRF-SMN, y opcionalmente añadir Open-Meteo y estabilizar respuestas vacías en alerts/patterns.
