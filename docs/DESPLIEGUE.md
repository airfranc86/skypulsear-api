# SkyPulse v2.0.0 - Guía de Despliegue

**Repositorio:** https://github.com/airfranc86/skypulsear-api  
**Frontend:** https://skypulse-ar.vercel.app

## Variables de Entorno en Render

- `METEOSOURCE_API_KEY` - API key de Meteosource
- `WINDY_POINT_FORECAST_API_KEY` - API key de Windy
- `LOG_LEVEL` = `INFO`
- `ENVIRONMENT` = `production`
- `PYTHON_VERSION` = `3.12`

## Verificación Post-Deploy

```bash
curl https://tu-api.onrender.com/health
curl https://tu-api.onrender.com/metrics
```

## Troubleshooting

**Error netCDF4:** Ya resuelto - netCDF4 comentado en requirements.txt  
**Error CORS:** Verificar que `https://skypulse-ar.vercel.app` está en `allow_origins`  
**Error 503:** Verificar variables de entorno en Render Dashboard

