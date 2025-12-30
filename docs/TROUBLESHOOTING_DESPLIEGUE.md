# 🔧 Troubleshooting de Despliegue - SkyPulse

## Error: netCDF4 no encuentra numpy durante compilación

### Síntoma
```
ModuleNotFoundError: No module named 'numpy'
error: metadata-generation-failed
```

### Causa
`netCDF4` necesita `numpy` instalado **antes** de compilarse, pero pip no garantiza el orden de instalación desde `requirements.txt`.

### Solución

El `buildCommand` en `render.yaml` ya está configurado para instalar en el orden correcto:

```yaml
buildCommand: |
  apt-get update && apt-get install -y libhdf5-dev libnetcdf-dev && \
  pip install --upgrade pip && \
  pip install --no-cache-dir numpy>=1.26.0 && \
  pip install --no-cache-dir --no-build-isolation netCDF4>=1.6.0 && \
  pip install --no-cache-dir -r requirements.txt
```

**Pasos:**
1. Verificar que `render.yaml` tiene el build command correcto
2. Si el error persiste, verificar que Render está usando `render.yaml`
3. Si Render no detecta `render.yaml`, configurar manualmente en Dashboard

### Alternativa: Sin netCDF4 (si no se usa WRF-SMN)

Si no estás usando WRF-SMN, puedes remover netCDF4 de `requirements.txt`:

```bash
# Comentar o remover estas líneas:
# netCDF4>=1.6.0
# xarray>=2023.1.0
# s3fs>=2023.1.0
```

Y simplificar el build command:

```yaml
buildCommand: |
  pip install --upgrade pip && \
  pip install -r requirements.txt
```

---

## Error: CORS en producción

### Síntoma
Frontend no puede hacer requests al backend, error CORS en consola del navegador.

### Solución

1. **Verificar CORS en `app/api/main.py`:**
   ```python
   allow_origins=[
       "https://skypulse-ar.vercel.app",  # Debe estar presente
       # ...
   ]
   ```

2. **Verificar que el dominio es exacto:**
   - No usar `*.vercel.app` si el dominio específico está disponible
   - Agregar el dominio exacto a la lista

3. **Verificar headers en respuesta:**
   ```bash
   curl -I https://tu-api.onrender.com/api/v1/weather/current?lat=-31.42&lon=-64.19
   # Debe incluir: Access-Control-Allow-Origin
   ```

---

## Error: Variables de entorno no configuradas

### Síntoma
```
Error 503: No hay fuentes de datos configuradas
```

### Solución

1. **Ir a Render Dashboard** → Tu servicio → Environment
2. **Agregar variables:**
   - `METEOSOURCE_API_KEY` = (tu API key)
   - `WINDY_POINT_FORECAST_API_KEY` = (tu API key)
   - `LOG_LEVEL` = `INFO`
   - `ENVIRONMENT` = `production`

3. **Reiniciar servicio** después de agregar variables

---

## Error: Circuit Breaker siempre abierto

### Síntoma
Todos los requests fallan con "Circuit breaker is OPEN"

### Solución

1. **Verificar conectividad con APIs externas:**
   ```bash
   # Desde Render logs, verificar errores de conexión
   ```

2. **Resetear circuit breaker:**
   - Esperar recovery timeout (60s por defecto)
   - O reiniciar el servicio en Render

3. **Verificar API keys:**
   - Verificar que las API keys son válidas
   - Verificar que no han expirado

---

## Error: Build timeout

### Síntoma
Build falla por timeout

### Solución

1. **Optimizar build command:**
   - Usar `--no-cache-dir` para pip
   - Instalar solo dependencias necesarias

2. **Verificar que no hay dependencias innecesarias:**
   - Revisar `requirements.txt`
   - Remover dependencias no usadas

---

## Error: Python version mismatch

### Síntoma
```
Python version X.X.X is not supported
```

### Solución

1. **Verificar `render.yaml`:**
   ```yaml
   envVars:
     - key: PYTHON_VERSION
       value: "3.12"
   ```

2. **O configurar en Render Dashboard:**
   - Environment → `PYTHON_VERSION` = `3.12`

---

## Error: Health check falla

### Síntoma
Render marca el servicio como unhealthy

### Solución

1. **Verificar health check path:**
   ```yaml
   healthCheckPath: /health
   ```

2. **Verificar que el endpoint responde:**
   ```bash
   curl https://tu-api.onrender.com/health
   # Debe retornar: {"status": "healthy", "service": "skypulse-api"}
   ```

3. **Verificar logs** para ver por qué falla el health check

---

## Error: Logs no estructurados

### Síntoma
Logs aparecen en formato texto plano en lugar de JSON

### Solución

1. **Verificar que `setup_logging()` se llama al inicio:**
   ```python
   # En app/api/main.py
   from app.utils.logging_config import setup_logging
   setup_logging()  # Debe estar antes de crear la app
   ```

2. **Verificar variable de entorno:**
   - `LOG_LEVEL` = `INFO` (o el nivel deseado)

---

## Error: Métricas no disponibles

### Síntoma
Endpoint `/metrics` retorna error o vacío

### Solución

1. **Verificar que `prometheus-client` está instalado:**
   ```bash
   # En requirements.txt debe estar:
   prometheus-client>=0.19.0
   ```

2. **Verificar que el router está registrado:**
   ```python
   # En app/api/main.py
   app.include_router(metrics.router, tags=["Metrics"])
   ```

3. **Verificar logs** para errores de importación

---

## Comandos Útiles para Debugging

### Ver logs en tiempo real
```bash
# En Render Dashboard → Logs
# O usar Render CLI:
render logs --service skypulse-api --tail
```

### Test de endpoints
```bash
# Health
curl https://tu-api.onrender.com/health

# Weather
curl "https://tu-api.onrender.com/api/v1/weather/current?lat=-31.42&lon=-64.19"

# Metrics
curl https://tu-api.onrender.com/metrics
```

### Verificar variables de entorno
```bash
# En Render Dashboard → Environment
# O agregar endpoint temporal para debug (solo en desarrollo):
@app.get("/debug/env")
async def debug_env():
    return {
        "has_meteosource": bool(os.getenv("METEOSOURCE_API_KEY")),
        "has_windy": bool(os.getenv("WINDY_POINT_FORECAST_API_KEY")),
    }
```

---

## Recursos

- [Render Documentation](https://render.com/docs)
- [Render Troubleshooting](https://render.com/docs/troubleshooting-deploys)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [netCDF4 Installation](https://unidata.github.io/netcdf4-python/)

