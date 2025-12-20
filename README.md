# SkyPulse API

API de decisiones meteorológicas para Argentina. Backend FastAPI desplegado en Render.

## Stack

- **Framework:** FastAPI
- **Runtime:** Python 3.12+
- **Deploy:** Render
- **Database:** Supabase (PostgreSQL)

## Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/weather/current` | Datos actuales fusionados |
| GET | `/api/v1/weather/forecast` | Pronóstico multi-modelo |
| POST | `/api/v1/risk-score` | Cálculo de riesgo por perfil |
| GET | `/api/v1/alerts` | Alertas meteorológicas |
| GET | `/api/v1/patterns` | Patrones argentinos detectados |

## Desarrollo Local

```bash
# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# Ejecutar servidor
uvicorn app.api.main:app --reload --port 8000
```

Abrir documentación: http://localhost:8000/docs

## Deploy en Render

1. Push a GitHub
2. Conectar repo en Render
3. Render detecta `render.yaml` automáticamente
4. Configurar variables de entorno en Render Dashboard
5. Deploy

## Estructura

```
app/
├── api/          # FastAPI endpoints
├── data/         # Repositorios y schemas
├── models/       # Modelos de datos
├── services/     # Lógica de negocio
└── utils/        # Utilidades
```

## Licencia

Propietario - Francisco A.

