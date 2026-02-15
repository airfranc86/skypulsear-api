# SkyPulse API

API REST de decisiones meteorológicas para Argentina. Backend FastAPI que fusiona datos de Windy (GFS/ECMWF) y WRF-SMN (AWS S3) mediante `UnifiedWeatherEngine`.

**Última actualización:** 2026-02-15  

**Auditoría de consistencia:** 2026-02-15 — Contrato de `/current` ampliado (precipitation, cloud_cover, timestamp, wind_direction_deg). Sub-scores de risk normalizados a 0–5 en la respuesta. Ver `.cursor/Docs/AUDITORIA-CONSISTENCIA-FRONTEND-BACKEND.md`.

**Risk Agents:** 2026-02-15 — Agentes de evaluación de riesgo en background (Operational Failure, Data Integrity, Model Drift). Opcionales; activación con `RISK_AGENTS_ENABLED=true`. Ver [docs/AUDITORIA_FASE_FEATURES_FIXES_RISK_AGENTS.md](../docs/AUDITORIA_FASE_FEATURES_FIXES_RISK_AGENTS.md).

---

## Descripción

- Expone tiempo actual y pronóstico horario fusionados.
- Calcula riesgo meteorológico por perfil (piloto, transportista, agricultor, etc.).
- Detecta patrones (tormentas convectivas, olas de calor/frío, heladas).
- Genera alertas meteorológicas con niveles compatibles con SMN Argentina.
- **El modelo WRF no se ejecuta en este servicio;** solo se ingieren datos ya publicados (Windy API + bucket S3 SMN).

---

## Requisitos

- Python 3.12+
- Dependencias en `app/requirements.txt`

---

## Instalación

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r app/requirements.txt
```

---

## Variables de entorno

| Variable | Descripción |
|---------|-------------|
| `VALID_API_KEYS` | Claves API válidas separadas por coma (ej. `skypulse-wrf-smn-aws`). **Requerido en producción.** |
| `WINDY_POINT_FORECAST_API_KEY` | API key de Windy para pronóstico (GFS). |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Opcionales; si no se setean, el acceso a WRF-SMN es anónimo (bucket público `smn-ar-wrf`). |
| `AWS_DEFAULT_REGION` | Región AWS (default: `us-west-2`). |
| `RISK_AGENTS_ENABLED` | Opcional. Si `true`, ejecuta Risk Evaluation Agents en background cada 60 s y expone métricas `skypulse_risk_agent_*` en `/api/v1/metrics`. Default: `false`. |

---

## Ejecución local

```bash
cd apps/api
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

- Docs: http://localhost:8000/docs  
- Health: http://localhost:8000/api/v1/health  

Las peticiones a endpoints protegidos deben incluir el header `X-API-Key: <clave>` (una de las definidas en `VALID_API_KEYS`).

---

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/health` | Estado del servicio |
| GET | `/api/v1/weather/current` | Tiempo actual (lat, lon) |
| GET | `/api/v1/weather/forecast` | Pronóstico (lat, lon, days u hours) |
| POST | `/api/v1/risk-score` | Puntuación de riesgo por perfil |
| GET | `/api/v1/alerts` | Alertas meteorológicas |
| GET | `/api/v1/patterns` | Patrones detectados |
| GET | `/api/v1/metrics` | Métricas Prometheus |

### Contrato y unidades (consistencia con el dashboard)

- **GET /weather/current**: `current` incluye `temperature` (°C), `humidity` (%), `wind_speed` (m/s), **`wind_speed_kmh`** (km/h, para uso directo en la UI), `wind_direction`, `wind_direction_deg`, `pressure` (hPa), `precipitation` (mm), `cloud_cover` (%), `weather_code`, `timestamp` (ISO). El frontend usa `wind_speed_kmh` en todo el sistema.
- **GET /weather/forecast**: cada ítem tiene `temperature` (°C), `precipitation` (mm), `wind_speed` (m/s), **`wind_speed_kmh`** (km/h). El frontend usa los valores de la API.
- **POST /risk-score**: body `{ "lat", "lon", "profile", "hours_ahead" }`. Respuesta: `score` (0–5), `risk_score_100`, sub-scores `temperature_risk`, `wind_risk`, etc. en **escala 0–5** (el router convierte internamente de 0–100 a 0–5). El frontend multiplica sub-scores por 20 para barras 0–100.

Auditoría detallada frontend–backend: ver [.cursor/Docs/AUDITORIA-CONSISTENCIA-FRONTEND-BACKEND.md](../../.cursor/Docs/AUDITORIA-CONSISTENCIA-FRONTEND-BACKEND.md).

---

## Risk Evaluation Agents (opcional)

Si `RISK_AGENTS_ENABLED=true`, se ejecutan en background cada 60 s tres agentes que solo exponen métricas (no alteran respuestas ni contratos):

| Agente | Métrica | Descripción |
|--------|---------|-------------|
| Operational Failure | `skypulse_risk_agent_circuit_open{circuit_name}` | 1 si el circuit breaker del proveedor está abierto, 0 si cerrado/half_open. |
| Data Integrity | `skypulse_risk_agent_data_integrity_ok` | 1 si datos recientes ok, 0 si problemas de integridad. |
| Model Drift | `skypulse_risk_agent_model_drift_confidence` | Confianza/skill 0–1 cuando hay observación (skeleton por defecto). |

- **Ubicación:** `app/services/risk_agents/` (base, operational_failure, data_integrity, model_drift).
- **Rollback:** Desactivar con `RISK_AGENTS_ENABLED=false` y redeploy; no hay cambios de contrato API.
- **Documentación:** [docs/AUDITORIA_FASE_FEATURES_FIXES_RISK_AGENTS.md](../docs/AUDITORIA_FASE_FEATURES_FIXES_RISK_AGENTS.md) (métricas, umbrales sugeridos, procedimiento de rollback).

---

## Fuentes de datos

Ver [FUENTES_PREDICCION.md](./FUENTES_PREDICCION.md).

- **Windy:** GFS (y opcionalmente ECMWF) vía API Point Forecast.
- **WRF-SMN:** Datos NetCDF del bucket público AWS `smn-ar-wrf` (SMN Argentina). Solo lectura; WRF no se ejecuta en este servicio.

---

## Estructura relevante

```
apps/api/
├── app/
│   ├── api/           # Routers, dependencies, middleware
│   ├── data/          # Repositories, schemas, processors
│   ├── services/      # UnifiedWeatherEngine, risk, alerts, patterns, risk_agents
│   ├── models/
│   └── utils/         # circuit_breaker, circuit_breaker_registry, metrics
├── app/requirements.txt
├── FUENTES_PREDICCION.md
└── README.md
```

---

## Despliegue (Render)

- Servicio web; comando de inicio: `uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
- Build: `pip install -r app/requirements.txt` (desde la raíz del repo o desde `apps/api` según configuración).
- Configurar `VALID_API_KEYS` en Environment del servicio.

---

## Licencia

Uso según el proyecto SkyPulse.
