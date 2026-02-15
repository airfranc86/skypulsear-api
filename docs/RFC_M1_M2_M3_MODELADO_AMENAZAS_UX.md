# RFC M1 / M2 / M3 — Modelado híbrido, motor de amenazas, UX seguridad aeronáutica

**Rol:** Chief Systems Architect & Lead Operational Meteorologist  
**Fecha:** 2026-02-15  
**Prioridad:** M1 → M2 → M3  
**Restricciones:** Backward compatibility, zero downtime, feature toggles, circuit breaker, no romper contrato API.

---

## 1. Auditoría técnica actual

### Módulos y archivos relevantes

| Área | Archivos / módulos | Estado |
|------|--------------------|--------|
| **Fuentes de datos** | `app/data/repositories/base_repository.py` (IWeatherRepository), `windy_repository.py`, `wrfsmn_repository.py`, `repository_factory.py` | WRF-SMN existe (S3 NetCDF); deshabilitado por defecto; no GRIB2. |
| **Fusión** | `app/services/unified_weather_engine.py`, `app/data/processors/weather_normalizer.py`, `weather_fusion.py` | Fusión Windy + opcional WRF; normalizer con WeatherSource.WRF_SMN. |
| **Amenazas / patrones** | `app/services/pattern_detector.py`, `alert_service.py`, `risk_scoring.py` | Patrones y alertas; no hay Shelf/Wall Cloud ni proxy granizo explícito ni GOES-16/SINARAME. |
| **API** | `app/api/routers/weather.py`, `alerts.py`, `patterns.py`, `risk.py` | Contrato actual estable; sin endpoints específicos para amenazas clasificadas. |
| **Frontend** | `apps/web/dashboard.html` | Sin badges OMM/OHMC (VFR/MVFR/IFR/LIFR); sin LST heladas. |
| **Infra** | `app/utils/circuit_breaker.py`, `circuit_breaker_registry.py`, Risk Agents | Circuit breaker en Windy; Risk Agents operativos. |

### Dependencias actuales

- **Backend:** FastAPI, boto3, s3fs, xarray, netCDF4 (WRF-SMN), requests (Windy), prometheus_client.
- **Frontend:** Vanilla JS, Open-Meteo client, API SkyPulse.

### Puntos de acoplamiento

- `UnifiedWeatherEngine` → `RepositoryFactory` → Windy / WRF-SMN.
- Routers → `UnifiedWeatherEngine`, `PatternDetector`, `AlertService`, `RiskScoringService`.
- Dashboard → `CONFIG.backendUrl`, `/weather/current`, `/weather/forecast`, `/alerts`, `/patterns`, `/risk-score`.

---

## 2. Análisis de brecha

### M1 — Modelado híbrido (WRF-SMN)

| Qué existe | Qué falta | Riesgo |
|------------|-----------|--------|
| IWeatherRepository, WRFSMNRepository (S3 NetCDF) | Interfaz WeatherProvider unificada nombrada; adapter explícito WRF; ingesta GRIB2 si se exige formato GRIB2 (hoy es NetCDF) | Bajo si se mantiene NetCDF; medio si se añade pipeline GRIB2. |
| RepositoryFactory, fallback GFS vía Windy | Circuit breaker en WRF (hoy solo Windy); TTL/cache explícito documentado; feature toggle por fuente | Bajo. |
| WRF deshabilitado por defecto | Habilitación por zona (ej. Córdoba primero); worker/Lambda opcional para ingesta asíncrona | Medio (costo/arquitectura). |

### M2 — Motor de clasificación de amenazas

| Qué existe | Qué falta | Riesgo |
|------------|-----------|--------|
| PatternDetector, AlertService, RiskScoringService | Separación explícita: cálculo físico vs heurística vs etiquetado visual | Medio. |
| Alertas por nivel (0–4) | Lógica Shelf Cloud vs Wall Cloud; proxy granizo (>50–55 dBZ bajo 0°C); validación GOES-16 + Radar SINARAME | Alto (datos GOES/SINARAME, integración SMN). |
| API de alertas y patrones | Endpoint o campos solo con resultados interpretados (sin bloquear frontend); métricas de validación y falsos positivos | Bajo. |

### M3 — UX/UI seguridad aeronáutica

| Qué existe | Qué falta | Riesgo |
|------------|-----------|--------|
| Dashboard con riesgo y alertas | Badges dinámicos OMM/OHMC; código de colores VFR/MVFR/IFR/LIFR estricto | Bajo. |
| Layout y contrato API actual | Variable LST GOES-16 (alerta heladas ≤ 3°C); feature toggle visual; garantía de no regresión | Medio (datos LST, cambios UI). |

---

## 3. Arquitectura propuesta

### M1 — Modelado híbrido

- **Actual:** RepositoryFactory → WindyRepository | WRFSMNRepository (NetCDF S3); UnifiedWeatherEngine orquesta; sin circuit breaker en WRF.
- **Propuesta:**
  - Mantener IWeatherRepository como contrato; opcionalmente introducir nombre `WeatherProvider` en documentación/refactor menor.
  - Adapter WRF: capa delgada que implemente IWeatherRepository y delegue a WRFSMNRepository; mismo contrato, posible futura fuente GRIB2 detrás.
  - Circuit breaker para WRF (registro voluntario como en Windy); fallback: si WRF falla o no cubre, usar solo GFS (Windy).
  - Cache: TTL explícito (ej. 6 h) en WRF; documentar en config.
  - Ingesta: mantener síncrona en API; worker/Lambda solo si se justifica por costos/latencia (RFC aparte).
- **Flujo:** Request → UnifiedWeatherEngine → Factory → Windy (siempre) + WRF (si habilitado y circuit cerrado) → normalizer → fusión → respuesta.

### M2 — Motor de clasificación de amenazas

- **Separación:** (1) Capa física: dBZ, 0°C, umbrales; (2) Heurística: Shelf vs Wall, proxy granizo; (3) Etiquetado: nivel de alerta y texto para UI.
- **Fuentes:** Datos actuales (radar/modelo) + futura integración GOES-16/SINARAME cuando estén disponibles; exponer solo resultados interpretados (niveles, labels).
- **Ubicación:** Servicio nuevo o extensión de PatternDetector/AlertService; ejecución server-side; no bloquear render del frontend.
- **Flujo:** Datos crudos → motor de clasificación → resultados interpretados → API (alerts/patterns o endpoint dedicado) → frontend.

### M3 — UX/UI seguridad aeronáutica

- **Badges y colores:** Verde VFR, Azul MVFR, Naranja IFR, Rojo LIFR; criterios derivados de API (visibilidad, techo, etc.) o de un endpoint que devuelva categoría de vuelo.
- **LST heladas:** Cuando exista variable LST (GOES-16 o equivalente), umbral ≤ 3°C → alerta heladas; integración en dashboard sin romper layout.
- **Feature toggle:** Variable de entorno o flag para activar/desactivar badges y colores OMM/OHMC en el frontend.

### Diagrama de alto nivel (objetivo)

```
[Cliente] → [API] → [UnifiedWeatherEngine] → [Windy] + [WRF Adapter] (M1)
                              ↓
                    [Normalizer] → [Fusión]
                              ↓
                    [Motor Amenazas] (M2) → resultados interpretados
                              ↓
                    [Routers] → [Cliente]
                              ↓
                    [Dashboard] (M3) → Badges VFR/MVFR/IFR/LIFR, LST heladas
```

---

## 4. Análisis de riesgo operativo

| Aspecto | M1 | M2 | M3 |
|---------|----|----|-----|
| **Performance** | Latencia S3/NetCDF; cache y circuit breaker limitan impacto | Cálculo server-side acotado; sin bloqueo de requests | Cambios CSS/JS; impacto bajo si se mantiene layout |
| **Costos** | S3 público sin costo de datos; posibles costos si se usa Lambda/worker | Sin costos adicionales de datos si se usan fuentes actuales | Ninguno |
| **Latencia** | WRF puede añadir ~1–3 s por request si no hay cache; TTL reduce llamadas | Aumento acotado si el motor es ligero | Despreciable |
| **Escenarios de falla** | WRF no disponible → fallback GFS; circuit abierto → solo Windy | Motor falla → degradar a alertas actuales; no exponer errores internos | Toggle desactiva nuevos elementos |
| **Rollback** | Deshabilitar WRF en factory; redeploy sin cambio de contrato | Feature toggle del motor; respuesta de alertas sin campos nuevos | Feature toggle visual; revert commit frontend |

---

## 5. Plan de implementación en 5 pasos (por módulo)

### M1 — Modelado híbrido

1. **Paso 1:** Añadir circuit breaker a WRFSMNRepository y registrarlo en circuit_breaker_registry; feature toggle `WRF_SMN_ENABLED` (default false); sin cambiar contrato.
2. **Paso 2:** Documentar interfaz “WeatherProvider” (alias de IWeatherRepository) y adapter WRF como capa delgada si se desea; habilitar WRF por config en factory cuando `WRF_SMN_ENABLED=true`.
3. **Paso 3:** TTL explícito (ej. 6 h) en cache WRF; documentar en README y en variables de entorno.
4. **Paso 4:** Pruebas de integración: Córdoba/Resistencia con WRF habilitado; validar fallback a GFS si WRF falla.
5. **Paso 5:** Observabilidad: métricas de latencia y uso WRF; rollback: `WRF_SMN_ENABLED=false` y redeploy.

### M2 — Motor de clasificación de amenazas

1. **Paso 1:** Definir contrato de salida (estructura de “amenaza clasificada”: tipo, nivel, etiqueta, criterio usado); sin cambiar contratos públicos existentes.
2. **Paso 2:** Implementar lógica física (umbrales dBZ, 0°C) y heurística Shelf vs Wall y proxy granizo en módulo dedicado; alimentado por datos actuales (modelo/radar disponible).
3. **Paso 3:** Integrar en pipeline de alertas/patrones; exponer solo resultados interpretados; feature toggle `THREAT_CLASSIFICATION_ENABLED`.
4. **Paso 4:** Cuando existan fuentes GOES-16/SINARAME, añadir validación cruzada; métricas de validación y falsos positivos.
5. **Paso 5:** Documentar métricas y umbrales; rollback vía toggle.

### M3 — UX/UI seguridad aeronáutica

1. **Paso 1:** Definir criterios VFR/MVFR/IFR/LIFR (a partir de datos actuales de API o endpoint derivado); documentar en auditoría frontend-backend.
2. **Paso 2:** Implementar badges dinámicos y paleta de colores (Verde/Azul/Naranja/Rojo) en dashboard; feature toggle visual.
3. **Paso 3:** Cuando exista LST (GOES-16 o equivalente), integrar umbral ≤ 3°C para alerta heladas; mostrar en dashboard sin romper layout.
4. **Paso 4:** Pruebas de regresión UI; revisión de accesibilidad y contraste.
5. **Paso 5:** Rollback: desactivar toggle; revert de cambios frontend si es necesario.

---

## 6. Estrategia de observabilidad

- **M1:** Métricas: latencia WRF, cache hit/miss, estado circuit breaker WRF; logs estructurados en fallos S3; alertas si circuit abierto > N minutos.
- **M2:** Métricas: clasificaciones por tipo (Shelf/Wall/granizo), tiempo de cómputo, errores del motor; no exponer datos crudos en logs.
- **M3:** Sin métricas específicas de backend; opcional: eventos de uso de badges en frontend (analytics).

---

## 7. Costos y cuotas (M1)

- **AWS S3 (smn-ar-wrf):** Open Data, sin costo de transferencia para lectura; posibles costos si se usa Lambda/worker en cuenta propia (no requerido en pasos 1–5).
- **Cuotas:** Límites de request a S3; cache y TTL reducen llamadas; circuit breaker evita saturación en fallos.

---

## 8. Criterio de evaluación

- **Extensible:** M1 permite añadir más fuentes vía IWeatherRepository; M2 permite nuevas reglas sin romper contrato; M3 permite más badges o fuentes LST.
- **Resiliente:** Fallback GFS, circuit breaker, feature toggles, degradación sin romper API.
- **Auditable:** Logs y métricas por módulo; documentos RFC y auditoría.
- **Reversible:** Toggles y rollback por pasos sin cambios destructivos del contrato API.

---

**Siguiente paso recomendado:** Implementar M1 Pasos 1–2 (circuit breaker WRF, feature toggle `WRF_SMN_ENABLED`, documentar adapter); luego M2 Paso 1 (contrato de salida del motor de amenazas); luego M3 Paso 1 (criterios VFR/MVFR/IFR/LIFR). Cada paso con validación y posibilidad de rollback.
