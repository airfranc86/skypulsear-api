# Auditoría de consistencia Frontend–Backend — SkyPulse Dashboard

**Fecha:** 2026-02-15  
**Alcance:** Contrato API, mapeo de campos, unidades, valores de borde y tolerancia a errores entre el dashboard (apps/web) y la API (apps/api).

---

## 1. Executive summary

Se auditaron los endpoints consumidos por el dashboard (`/api/v1/weather/current`, `/forecast`, `/risk-score`, `/alerts`, `/patterns`) y el mapeo de datos en `dashboard.html` y `api-client.js`.

**Hallazgos principales:**

- **Unidades:** La API devuelve `wind_speed` en **m/s**; el frontend ya convierte a **km/h** (× 3.6) al construir `current` y `hourly`, por lo que el display y el cálculo de riesgo local son coherentes.
- **Dirección del viento:** La API expone solo `wind_direction` como **cardinal (string)** ("N", "S", …); no expone `wind_direction_deg`. El frontend acepta string o número; si recibe string, la etiqueta se muestra bien pero el color por dirección usa fallback (no hay grados).
- **Campos faltantes en `/current`:** La API no devuelve `precipitation`, `cloud_cover`, `weather_code`, `timestamp` ni `apparent_temperature` en el objeto `current`. El frontend rellena con `0` o valores por defecto, por lo que no rompe pero muestra datos incompletos (p. ej. nubosidad y precipitación en 0 cuando la fuente es backend).
- **Risk-score:** El frontend espera sub-scores en escala **0–5** y los multiplica por 20 para barras 0–100. El servicio interno devuelve sub-scores en **0–100**; el router los expone sin convertir. Si el backend envía 0–100, el frontend mostraría barras desproporcionadas; debe existir conversión en backend o ajuste en frontend.
- **Alertas:** Contrato alineado (level, level_name, phenomenon, description, time_window, recommendations). El frontend usa `level_name`, `phenomenon`, `time_window`; `recommendations` es array y el frontend usa el primer ítem donde aplica.
- **Null/undefined:** El frontend usa `?? 0` o `!= null` en la mayoría de los campos mostrados; hay buena tolerancia a campos ausentes.

**Riesgo global:** Medio. Las correcciones prioritarias son: (1) ampliar el contrato de `/current` con los campos que el frontend ya usa, (2) unificar escala de sub-scores de risk (0–5 en API) y (3) opcionalmente exponer `wind_direction_deg` para color/rotación del viento.

---

## 2. Tabla de consistencia campo a campo

### 2.1 GET `/api/v1/weather/current`

| Campo en frontend       | Campo en backend   | Tipo backend | Unidad API | Unidad UI | Conversión | Inconsistencia | Riesgo | Caso de prueba |
|-------------------------|--------------------|-------------|------------|-----------|------------|----------------|--------|-----------------|
| `temperature_2m`        | `current.temperature` | number    | °C         | °C        | Ninguna   | Ninguna        | Low    | `temperature: 22` → muestra 22°C |
| `apparent_temperature`  | —                  | —           | —          | °C        | —          | **API no envía**; frontend usa `c.temperature` como fallback | Medium | Backend: sin campo → UI muestra temp real como sensación |
| `relative_humidity_2m` | `current.humidity` | number      | %          | %         | Ninguna   | Ninguna        | Low    | `humidity: 65` → 65% |
| `wind_speed_10m`       | `current.wind_speed` | number    | **m/s**    | **km/h**  | **× 3.6** en frontend | Ninguna (ya corregido) | Low    | `wind_speed: 5` → 18 km/h |
| `wind_direction_10m`   | `current.wind_direction` | **string** (cardinal) | —  | cardinal  | Frontend acepta string o número | API no envía grados; color por dirección usa fallback | Low    | `wind_direction: "S"` → "Del S" ✓; color no por ángulo |
| `wind_gusts_10m`       | —                  | —           | —          | km/h      | Frontend: `wind_speed_10m * 1.2` | Estimado en frontend desde viento actual | Low    | — |
| `precipitation`        | —                  | —           | —          | mm        | —          | **API no envía**; frontend usa 0 | Medium | Siempre 0 cuando fuente = backend |
| `weather_code`         | —                  | —           | —          | —         | —          | **API no envía**; frontend usa 0 | Low    | Ícono genérico |
| `cloud_cover`          | —                  | —           | —          | %         | —          | **API no envía**; frontend usa 0 | Medium | Nubosidad siempre 0 con backend |
| `surface_pressure`     | `current.pressure` | number      | hPa        | Pa (×100) | Frontend: `pressure * 100` | API en hPa, UI conceptualmente en Pa; valor correcto para display si se muestra en hPa | Low    | `pressure: 1013` → 101300 Pa (mostrar como 1013 hPa) |
| `time`                 | —                  | —           | —          | ISO string| —          | **API no envía**; frontend usa `new Date().toISOString()` | Low    | — |
| `uv_index`             | —                  | —           | —          | —         | —          | **API no envía**; frontend fija 5 | Low    | — |

**Esquema JSON real (producción) `/current`:**

```json
{
  "location": { "lat": -34.6, "lon": -58.4 },
  "current": {
    "temperature": 22.5,
    "humidity": 65,
    "wind_speed": 5.2,
    "wind_direction": "S",
    "pressure": 1013,
    "conditions": "parcialmente nublado"
  },
  "source": "fused",
  "meteo_source_display": "Windy GFS + ECMWF, WRF-SMN",
  "authentication": "protected",
  "api_key_valid": true
}
```

### 2.2 GET `/api/v1/weather/forecast`

| Campo en frontend    | Campo en backend | Tipo  | Unidad API | Unidad UI | Conversión | Inconsistencia | Riesgo |
|----------------------|------------------|-------|------------|-----------|------------|----------------|--------|
| `time`               | `forecast[].timestamp` | string ISO | — | — | Frontend usa tal cual | Ninguna | Low |
| `temperature_2m`     | `forecast[].temperature` | number | °C | °C | Ninguna | Ninguna | Low |
| `precipitation`     | `forecast[].precipitation` | number | mm | mm | Ninguna | Ninguna | Low |
| `wind_speed_10m`     | `forecast[].wind_speed` | number | **m/s** | **km/h** | **× 3.6** en frontend | Ninguna | Low |

**Esquema ítem de forecast:**

```json
{
  "date": "2026-02-15",
  "timestamp": "2026-02-15T12:00:00+00:00",
  "temperature": 24.0,
  "precipitation": 0.0,
  "wind_speed": 3.1,
  "conditions": "despejado"
}
```

### 2.3 POST `/api/v1/risk-score`

| Campo en frontend | Campo en backend     | Tipo   | Escala API | Escala UI    | Conversión frontend | Inconsistencia | Riesgo |
|-------------------|----------------------|--------|------------|-------------|---------------------|----------------|--------|
| `score`           | `score`              | float  | 0–5        | 0–5 (gauge) | Ninguna             | Ninguna        | Low    |
| `tempRisk`        | `temperature_risk`  | float  | **0–5** (contract) / 0–100 (servicio) | 0–100 (barra) | `* 20` | **Backend puede enviar 0–100**; si es así, barras se disparan | **High** | Ver nota 1 |
| `windRisk`        | `wind_risk`          | float  | 0–5        | 0–100       | `* 20`              | Misma que arriba | High   |
| `precipRisk`      | `precipitation_risk` | float  | 0–5        | 0–100       | `* 20`              | Misma           | High   |
| `stormRisk`       | `storm_risk`         | float  | 0–5        | 0–100       | `* 20`              | Misma           | High   |
| `hailRisk`        | `hail_risk`          | float  | 0–5        | 0–100       | `* 20`              | Misma           | High   |
| `patternRisk`     | `pattern_risk`       | float  | 0–5        | 0–100       | `* 20`              | Misma           | High   |

**Nota 1:** En código, `RiskScoringService` devuelve sub-scores en **0–100**; `RiskScoreResponse` declara `ge=0, le=5`. Si no hay conversión en el router, o la validación no se aplica, el cliente podría recibir 0–100 y el frontend mostraría valores × 20 (p. ej. 2000). **Acción:** Normalizar en backend a 0–5 antes de enviar (dividir por 20) o documentar y cambiar frontend a dividir por 20 si API envía 0–100.

**Ejemplo de respuesta esperada por el frontend:**

```json
{
  "score": 2.1,
  "category": "moderado",
  "risk_score_100": 42.0,
  "temperature_risk": 1.5,
  "wind_risk": 2.0,
  "precipitation_risk": 0.5,
  "storm_risk": 0.0,
  "hail_risk": 0.0,
  "pattern_risk": 0.0,
  "alert_risk": 0.0,
  "apparent_temperature": 23.5,
  "recommendations": ["..."],
  "key_factors": [],
  "confidence": 0.8
}
```

### 2.4 GET `/api/v1/alerts`

| Campo en frontend   | Campo en backend | Tipo   | Inconsistencia | Riesgo |
|---------------------|------------------|--------|----------------|--------|
| `level`             | `level`          | int 0–4 | Ninguna | Low |
| `level_name`        | `level_name`     | string | Ninguna | Low |
| `phenomenon`        | `phenomenon`     | string | Ninguna | Low |
| `description`       | `description`    | string | Ninguna | Low |
| `time_window`       | `time_window`    | string | Ninguna | Low |
| `recommendation(s)` | `recommendations` (array) | list[str] | Frontend usa primer ítem o mapeo; singular en ejemplos | Low |

Contrato alineado; el frontend usa snake_case de la API.

### 2.5 GET `/api/v1/patterns`

El dashboard no muestra actualmente el listado detallado de patrones en la UI principal; se consumen para risk/alertas. Contrato: `location`, `patterns[]`, `pattern_count`, `max_risk_level`. Sin inconsistencias críticas detectadas para el uso actual.

---

## 3. Inconsistencias identificadas con impacto

| ID | Descripción | Impacto | Ubicación |
|----|-------------|---------|-----------|
| I1 | **API `/current` no envía** `precipitation`, `cloud_cover`, `weather_code`, `timestamp`, `apparent_temperature` | Nubosidad y precipitación en 0; sensación térmica = temperatura real; hora de observación genérica | Backend `_unified_to_current_response` |
| I2 | **API solo envía dirección de viento como cardinal** (string); no `wind_direction_deg` | No se puede colorear/rotar ícono por ángulo; solo etiqueta correcta | Backend weather router |
| I3 | **Sub-scores de risk en escala 0–100 en servicio vs 0–5 en API** | Si el router no convierte, el frontend muestra barras de riesgo desproporcionadas (hasta 2000) | Backend risk router / RiskScoringService |
| I4 | **Presión:** API en hPa, frontend guarda `pressure * 100` como Pa | Coherente si la UI muestra en hPa (dividiendo por 100); verificar etiqueta de unidad en UI | Frontend normalización |
| I5 | **Risk:** Frontend asume score 0–5 y sub-scores 0–5**; servicio devuelve sub-scores 0–100 | Riesgo de doble interpretación si backend no normaliza | Backend + frontend |

---

## 4. Plan de corrección minimalista

1. **Backend – `/current` (prioridad alta)**  
   En `_unified_to_current_response`, añadir al objeto `current`:
   - `precipitation` (from `f.precipitation_mm`, unidad mm)
   - `cloud_cover` (from `f.cloud_cover_pct`, %)
   - `weather_code`: derivar o 0 si no existe en UnifiedForecast
   - `timestamp`: `f.timestamp.isoformat()` si existe
   - `apparent_temperature`: si UnifiedForecast lo expone; si no, omitir o igual a temperature
   - Opcional: `wind_direction_deg` (0–360) además de `wind_direction` (cardinal), para color/rotación en UI.

2. **Backend – Risk sub-scores (prioridad alta)**  
   En el router de risk, antes de construir `RiskScoreResponse`, convertir sub-scores de 0–100 a 0–5:
   - `temperature_risk_api = risk_score.temperature_risk / 20.0` (y análogo para wind, precipitation, storm, hail, pattern, alert).
   - Asegurar que `RiskScoreResponse` reciba siempre valores en 0–5 y que el servicio documente que internamente trabaja en 0–100.

3. **Frontend – Tolerancia a sub-scores**  
   Si el backend pudiera enviar 0–100 en una transición: en `fetchRiskScoreFromBackend`, detectar rango (p. ej. si `response.temperature_risk > 5`) y normalizar: `value = value > 5 ? value / 20 : value`, luego `* 20` para barras. Así se evita barras rotas aunque el backend no convierta aún.

4. **Documentación**  
   - En API: documentar en OpenAPI/README unidades (wind_speed m/s, pressure hPa, temperature °C) y escalas (risk score 0–5, sub-scores 0–5).
   - En frontend: documentar en README que `wind_speed_10m` y series horarias de viento se almacenan en km/h tras conversión desde m/s.

5. **Validación de precisión física**  
   - Backend: UnifiedForecast ya restringe temperatura (-100–60 °C), viento (0–150 m/s), etc.
   - Frontend: al mostrar, evitar `undefined`/NaN con `current.field != null ? current.field : '—'` (ya usado en la mayoría de métricas).

---

## 5. Verificación de tolerancia a errores y tests sugeridos

### 5.1 Casos manuales recomendados

| Caso | Acción | Resultado esperado |
|------|--------|--------------------|
| API `/current` sin `wind_speed` | Enviar `current` sin clave `wind_speed` | Frontend usa 0; no excepción; risk de viento 0 |
| API `/current` con `wind_direction: null` | Enviar null | Frontend muestra "—" (getWindDirectionLabel) |
| API `/current` con `temperature: "22"` (string) | Enviar string numérico | Frontend puede mostrar "22" o coercion; idealmente backend envía number |
| API `/risk-score` con `temperature_risk: 50` (0–100) | Llamar risk-score que devuelva 50 | Sin corrección: barra 1000; con normalización frontend: barra 100 o 50 según lógica |
| API timeout / 503 | Desconectar backend o devolver 503 | Fallback a Open-Meteo o datos de ejemplo; mensaje al usuario |

### 5.2 Script sugerido para validación automatizada

Script (Node o Python) que:

1. **Contrato `/current`:**  
   GET `/api/v1/weather/current?lat=-34.6&lon=-58.4` con API key; comprobar que existan `current.temperature`, `current.humidity`, `current.wind_speed`, `current.wind_direction`, `current.pressure`; tipos number/string según tabla; `wind_speed` en rango razonable (0–50 m/s).

2. **Contrato `/forecast`:**  
   GET forecast; comprobar que cada ítem tenga `timestamp`, `temperature`, `precipitation`, `wind_speed`; tipos y rangos plausibles.

3. **Contrato `/risk-score`:**  
   POST con `{ "lat": -34.6, "lon": -58.4, "profile": "piloto", "hours_ahead": 6 }`; comprobar que `score` esté en [0, 5] y que cada sub-score (`temperature_risk`, `wind_risk`, …) esté en [0, 5]. Si algún sub-score > 5, marcar como fallo de consistencia.

4. **Unidades:**  
   Tras GET current, comprobar que `wind_speed` sea numérico y en m/s (p. ej. < 50); opcionalmente comparar con respuesta del motor de fusión (m/s).

Script de validación automatizada: **`scripts/validate-api-contract.mjs`**. Ejecución:

```bash
API_BASE_URL=https://skypulsear-api.onrender.com API_KEY=tu-clave node scripts/validate-api-contract.mjs
```

Comprueba: tipos y rangos de `/current`, ítems de `/forecast`, y que los sub-scores de `/risk-score` estén en [0, 5].

---

## 6. Resumen de cambios ya realizados (referencia)

- **Viento:** Backend: dirección en convención meteorológica “desde dónde sopla” (Windy + WRF-SMN). Frontend: conversión m/s → km/h (× 3.6) al construir `current` y `hourly` desde backend y Open-Meteo; riesgo de viento y display en km/h coherentes.
- **Fuente de datos:** API expone `meteo_source_display`; frontend muestra etiqueta “camuflada” (sin guiones bajos).
- **Dirección en UI:** `getWindDirectionLabel` acepta grados (número) o cardinal (string); si la API envía solo cardinal, la etiqueta es correcta y el color usa valor por defecto.

Este documento debe actualizarse cuando se amplíe el contrato de `/current`, se unifique la escala de risk o se añadan nuevos endpoints consumidos por el dashboard.
