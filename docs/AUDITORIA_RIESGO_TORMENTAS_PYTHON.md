# Auditoría técnica Python — Subsistema de riesgo, alertas y patrones (tormentas)

**Fecha:** 2026-02-15  
**Alcance:** risk, alerts, patterns (routers y servicios), risk_scoring, alert_service, pattern_detector, unified_weather_engine, normalized_weather, dependencies.  
**Reglas aplicadas:** .cursor/rules (testing-strategy, security, python-typing, error-handling, clean-code, api-fastapi-expert).

---

## 1. Resumen ejecutivo

- **Cumplimiento global:** El subsistema cumple en funcionalidad y contrato API. Pylint 9.10/10. Hallazgos prioritarios: estilo (líneas largas, demasiadas variables/ramas en funciones), re-raise con `from e`, logging con f-strings en lugar de % lazy, y código duplicado entre routers (manejo 503).
- **Arquitectura:** Una sola implementación de riesgo: `RiskScoringService` en `risk_scoring.py`. La carpeta `app/services/risk/` fue eliminada (código muerto).
- **Dimensiones:** Type hints presentes en la mayoría de firmas; seguridad (require_api_key, validación Pydantic) correcta; manejo de errores mejorable (raise desde excepción, excepciones menos genéricas en unified_weather_engine); testing a ampliar (ver sección 3).

---

## 2. Por archivo / módulo

### 2.1 app/api/routers/risk.py

| Dimensión | Cumplimiento | Incidencias |
|-----------|--------------|-------------|
| Calidad/arquitectura | Alto | Línea 177 > 100 caracteres; demasiadas variables locales (21) y ramas (13) en `calculate_risk_score`. |
| Type hints | Alto | Firmas tipadas. |
| Manejo de errores | Medio | L215: re-raise sin `from e` (W0707). |
| Seguridad | Alto | require_api_key; RiskScoreRequest validado (lat/lon/hours_ahead). |
| Testing | Pendiente | Tests de integración POST /risk-score. |
| Documentación/API | Alto | Docstring y modelos Pydantic. |
| Rendimiento | Alto | Sin bucles innecesarios. |

**Recomendaciones:** (1) Acortar línea 177 o dividir en dos. (2) Extraer bloques de `calculate_risk_score` a funciones auxiliares para reducir variables/ramas. (3) `raise HTTPException(...) from e`. (4) Parámetro `api_key` marcado como usado por Depends; suprimir warning con `_` si no se usa.

---

### 2.2 app/api/routers/alerts.py

| Dimensión | Cumplimiento | Incidencias |
|-----------|--------------|-------------|
| Calidad/arquitectura | Alto | Demasiadas variables locales (17). |
| Type hints | Alto | Firmas tipadas. |
| Manejo de errores | Medio | L153: re-raise sin `from e`. |
| Seguridad | Alto | require_api_key. |
| Testing | Pendiente | Tests integración GET /alerts. |
| Documentación/API | Alto | Modelos y docstrings. |
| Rendimiento | Alto | — |

**Recomendaciones:** (1) L122: usar `max_level = max(max_level, alert.level)`. (2) Eliminar import no usado `Optional`. (3) `raise ... from e`.

---

### 2.3 app/api/routers/patterns.py

Cumplimiento similar a alerts: require_api_key, validación, manejo 503. Código duplicado con alerts y risk (bloques except + raise 503). Recomendación: extraer helper común para "log + raise 503".

---

### 2.4 app/services/risk_scoring.py

| Dimensión | Cumplimiento | Incidencias |
|-----------|--------------|-------------|
| Calidad/arquitectura | Medio | Línea 738 > 100 caracteres; muchas variables/ramas en `calculate_risk` y `_calculate_storm_risk`; demasiados argumentos en `calculate_risk` (6) y `_identify_main_factors` (8). |
| Type hints | Alto | Firmas tipadas. |
| Manejo de errores | Alto | Excepciones específicas no requeridas en lógica pura. |
| Seguridad | Alto | Sin input directo de usuario; umbrales constantes. |
| Testing | Pendiente | Tests unitarios por factor (temp, wind, precip, storm, hail, pattern). |
| Documentación/API | Alto | Docstrings y comentarios en umbrales. |
| Rendimiento | Alto | Sin bucles críticos. |

**Recomendaciones:** (1) Sustituir `elif` tras `return` por `if` (R1705). (2) L380/385: usar `max(max_temp, *apparent_temps)` y `min(min_temp, *apparent_temps)` donde aplique. (3) Agrupar parámetros en dataclass o TypedDict para reducir argumentos. (4) L427/458/491/563/654: no-else-return.

---

### 2.5 app/services/alert_service.py

Líneas largas (112, 422); logging con f-string (L173); consider-using-max (L185); demasiadas ramas (L261); no-else-return y f-string sin interpolación (L413). Recomendación: lazy % en logging; simplificar ramas.

---

### 2.6 app/services/pattern_detector.py

Líneas largas (240, 286, 335, 437); logging f-string (L134); argumento `current` no usado (L421); import no usado `NormalizedWeatherData`. Recomendación: eliminar import y marcar `current` con `_` si no se usa.

---

### 2.7 app/services/unified_weather_engine.py

| Dimensión | Cumplimiento | Incidencias |
|-----------|--------------|-------------|
| Calidad/arquitectura | Medio | Líneas largas; demasiados argumentos en una función (6). |
| Type hints | Alto | Firmas tipadas. |
| Manejo de errores | Bajo | W0718: `except Exception` en varios puntos; conviene excepciones más específicas. |
| Seguridad | Alto | Sin exposición de secretos. |
| Testing | Pendiente | Tests unitarios/integración del flujo get_unified_forecast. |
| Documentación/API | Alto | Docstrings. |
| Rendimiento | Medio | Revisar ThreadPoolExecutor y timeouts. |

**Recomendaciones:** (1) Sustituir `except Exception` por tipos concretos donde sea posible. (2) Lazy % en logging. (3) Import de `timedelta` en toplevel. (4) Eliminar import no usado `WeatherData` si aplica.

---

### 2.8 app/data/schemas/normalized_weather.py

Cumplimiento alto. Única incidencia: no-else-return en `get_confidence_level` (L228). Campo `weather_code` añadido en UnifiedForecast y NormalizedWeatherData.

---

### 2.9 app/api/dependencies.py

Trailing whitespace en varias líneas; imports fuera de toplevel (logging); lazy % en logging. Sin hallazgos de seguridad críticos. Recomendación: limpiar espacios y mover imports a toplevel si no hay dependencias circulares.

---

## 3. Resumen Pylint y Bandit

- **Pylint:** Ejecutado sobre los 9 archivos del alcance. Puntuación global **9.10/10**. Principales categorías: C (convención), R (refactor), W (warning). No se aplicaron cambios automáticos; las recomendaciones anteriores priorizan las que afectan mantenibilidad y buenas prácticas.
- **Bandit (SAST):** Ejecutado en el mismo alcance. En el entorno de ejecución (Python 3.14) Bandit lanzó excepciones al analizar cada archivo; se reportó "No issues identified" para el código que pudo procesar. Recomendación: ejecutar Bandit en entorno Python 3.11/3.12 para un informe completo y adjuntar salida a esta auditoría.

---

## 4. Lista de tests a añadir

Alineada con testing-strategy y pytest-best-practices:

1. **risk_scoring.py**
   - Tests unitarios: `_calculate_temperature_risk`, `_calculate_wind_risk`, `_calculate_precipitation_risk`, `_calculate_storm_risk`, `_calculate_hail_risk` con datos que superen umbrales (viento > moderate, precip > 0, weather_code 95/96/99/77).
   - Test: `calculate_risk` con lista de pronósticos vacía o mínima.
   - Test: `_score_to_category` para cada rango 0–5.

2. **pattern_detector.py**
   - Tests unitarios: detección de patrones (ola de calor, helada, tormenta severa) con listas de pronósticos mock.

3. **alert_service.py**
   - Tests unitarios: `generate_alerts` con patrones mock; comprobar niveles de alerta y recomendaciones.

4. **Integración**
   - POST `/api/v1/risk-score`: body válido (lat, lon, hours_ahead); comprobar 200, score en [0, 5], sub-scores en [0, 5].
   - GET `/api/v1/alerts`: comprobar 200 y estructura de respuesta.
   - GET `/api/v1/patterns`: comprobar 200 y estructura.

Estructura sugerida: `tests/unit/` para servicios, `tests/integration/` para endpoints.

---

## 5. Arquitectura documentada

- **Riesgo:** Una sola implementación activa: `RiskScoringService` en `app/services/risk_scoring.py`. El paquete `app/services/risk/` (service.py, profiles.py, calculator.py, factors.py) fue eliminado; no existían referencias desde el router ni desde `app.services.__init__`.
- **Flujo:** POST /risk-score → risk.py → UnifiedWeatherEngine (pronóstico) → PatternDetector → AlertService → RiskScoringService → respuesta 0–5 (sub-scores convertidos desde 0–100).
- **Perfil:** Siempre `UserProfile.GENERAL`; el campo `profile` en el body es opcional e ignorado.

---

## 6. Checklist resumido (testing-code-review-checklist)

| Criterio | Estado |
|----------|--------|
| Código sigue estilo del proyecto (PEP 8, línea ≤100) | Parcial (líneas largas en varios archivos) |
| Funciones pequeñas y enfocadas | Parcial (demasiadas variables/ramas en risk.py y risk_scoring.py) |
| Type hints en firmas | Sí |
| Validación de inputs (Pydantic) | Sí |
| Sin secretos en logs/respuestas | Sí |
| Manejo de errores con re-raise desde causa | Parcial (raise sin `from e` en risk y alerts) |
| Tests para nueva funcionalidad / críticos | Pendiente (lista en sección 4) |
| Docstrings en APIs públicas | Sí |
| Código deprecado eliminado | Sí (risk/) |

---

Este documento debe actualizarse cuando se corrijan incidencias prioritarias, se añadan los tests listados o se vuelva a ejecutar Pylint/Bandit en un entorno estable.
