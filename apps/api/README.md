# SkyPulse API

API REST de decisiones meteorológicas para Argentina. Backend FastAPI que fusiona datos de Windy (GFS/ECMWF) y WRF-SMN (AWS S3) mediante `UnifiedWeatherEngine`.

**Última actualización:** 2026-02-15

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
│   ├── services/      # UnifiedWeatherEngine, risk, alerts, patterns
│   ├── models/
│   └── utils/
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
