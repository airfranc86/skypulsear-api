# 🚀 Guía de Despliegue - SkyPulse v2.0.0

**Frontend:** Vercel (https://skypulse-ar.vercel.app)  
**Backend:** Render (FastAPI)

---

## 📋 Pre-requisitos

1. ✅ Cuenta en Render (https://render.com)
2. ✅ Cuenta en Vercel (https://vercel.com)
3. ✅ API Keys configuradas:
   - Meteosource API Key
   - Windy Point Forecast API Key
4. ✅ Código en repositorio Git (GitHub/GitLab)

---

## 🔧 Paso 1: Desplegar Backend en Render

### Opción A: Usando Render Dashboard

1. **Ir a Render Dashboard** → New → Web Service
2. **Conectar repositorio** (GitHub/GitLab)
3. **Configurar servicio:**
   - **Name:** `skypulse-api`
   - **Environment:** `Python 3`
   - **Region:** `Oregon` (o la más cercana)
   - **Branch:** `main` o `master`
   - **Root Directory:** (dejar vacío)
   - **Build Command:**
     ```bash
     apt-get update && apt-get install -y libhdf5-dev libnetcdf-dev && \
     pip install --upgrade pip && \
     pip install numpy>=1.26.0 && \
     PIP_BUILD_ISOLATION=false pip install netCDF4>=1.6.0 && \
     pip install -r requirements.txt
     ```
   - **Start Command:**
     ```bash
     uvicorn app.api.main:app --host 0.0.0.0 --port $PORT
     ```

4. **Configurar Variables de Entorno:**
   - `METEOSOURCE_API_KEY` = (tu API key)
   - `WINDY_POINT_FORECAST_API_KEY` = (tu API key)
   - `LOG_LEVEL` = `INFO`
   - `ENVIRONMENT` = `production`
   - `PYTHON_VERSION` = `3.12`

5. **Health Check Path:** `/health`

6. **Click "Create Web Service"**

### Opción B: Usando render.yaml (Recomendado)

1. **Push render.yaml al repositorio** (ya está incluido)
2. **Ir a Render Dashboard** → New → Blueprint
3. **Seleccionar repositorio** con `render.yaml`
4. **Render detectará automáticamente la configuración**
5. **Configurar variables de entorno manualmente** (las marcadas con `sync: false`)

---

## 🌐 Paso 2: Verificar Backend Desplegado

### 1. Health Check
```bash
curl https://tu-api.onrender.com/health
# Debe retornar: {"status": "healthy", "service": "skypulse-api"}
```

### 2. Root Endpoint
```bash
curl https://tu-api.onrender.com/
# Debe retornar información de la API
```

### 3. Métricas
```bash
curl https://tu-api.onrender.com/metrics
# Debe retornar métricas en formato Prometheus
```

### 4. Docs (Swagger)
Abrir en navegador: `https://tu-api.onrender.com/docs`

---

## 🎨 Paso 3: Configurar Frontend en Vercel

### 1. Configurar Proyecto

**Nota:** El nombre del proyecto debe estar en **minúsculas**.

```bash
# Si ya tienes el proyecto configurado, solo necesitas actualizar variables de entorno
# Si no, usar nombre en minúsculas:
vercel --name skypulse-ar
```

### 2. Variables de Entorno en Vercel

En Vercel Dashboard → Project Settings → Environment Variables:

- `API_BASE_URL` = `https://tu-api.onrender.com`
- (Opcional) `NEXT_PUBLIC_API_URL` = `https://tu-api.onrender.com`

### 3. Verificar CORS

Asegurarse que el backend tiene configurado:
- `https://skypulse-ar.vercel.app` en `allow_origins`
- `allow_credentials=True` si se usan cookies

---

## ✅ Paso 4: Verificación Post-Despliegue

### Backend

```bash
# 1. Health check
curl https://tu-api.onrender.com/health

# 2. Test de weather endpoint
curl "https://tu-api.onrender.com/api/v1/weather/current?lat=-31.42&lon=-64.19"

# 3. Test de risk score
curl -X POST https://tu-api.onrender.com/api/v1/risk-score \
  -H "Content-Type: application/json" \
  -d '{"lat": -31.42, "lon": -64.19, "profile": "piloto", "hours_ahead": 6}'
```

### Frontend

1. Abrir https://skypulse-ar.vercel.app/dashboard.html
2. Verificar que carga datos meteorológicos
3. Verificar que muestra risk scores
4. Verificar que muestra alertas
5. Abrir DevTools → Network y verificar:
   - Requests a API de Render
   - No hay errores CORS
   - Responses con status 200

---

## 🔍 Monitoreo

### Logs en Render

1. Ir a Render Dashboard → Tu servicio → Logs
2. Verificar:
   - Logs en formato JSON estructurado
   - Correlation IDs presentes
   - No hay errores críticos

### Métricas

1. Endpoint `/metrics` disponible
2. (Opcional) Configurar Prometheus para scraping
3. (Opcional) Configurar Grafana para visualización

---

## 🐛 Troubleshooting

### Error: CORS
**Síntoma:** Frontend no puede hacer requests  
**Solución:**
- Verificar que `https://skypulse-ar.vercel.app` está en `allow_origins` en `app/api/main.py`
- Verificar headers CORS en respuesta del backend

### Error: 503 Service Unavailable
**Síntoma:** API retorna 503  
**Solución:**
- Verificar variables de entorno en Render
- Verificar que API keys están configuradas
- Verificar logs en Render Dashboard

### Error: Circuit Breaker Open
**Síntoma:** Error 503 con mensaje "Circuit breaker is OPEN"  
**Solución:**
- Verificar conectividad con APIs externas
- Esperar recovery timeout (60s)
- Verificar logs para identificar causa

### Error: Build Failed
**Síntoma:** Build falla en Render  
**Solución:**
- Verificar que `requirements.txt` está actualizado
- Verificar que `render.yaml` tiene build command correcto
- Verificar logs de build en Render

---

## 📝 Checklist Final

- [ ] Backend desplegado en Render
- [ ] Variables de entorno configuradas
- [ ] Health check responde correctamente
- [ ] Frontend configurado en Vercel
- [ ] Variables de entorno en Vercel configuradas
- [ ] CORS configurado correctamente
- [ ] Frontend puede hacer requests al backend
- [ ] Datos meteorológicos se muestran correctamente
- [ ] Logs estructurados funcionando
- [ ] Métricas disponibles en `/metrics`

---

## 🎉 ¡Despliegue Completado!

Una vez completado el checklist, tu aplicación estará en producción:

- **Frontend:** https://skypulse-ar.vercel.app
- **Backend:** https://tu-api.onrender.com
- **Docs:** https://tu-api.onrender.com/docs
- **Métricas:** https://tu-api.onrender.com/metrics

---

## 📚 Recursos

- [Render Documentation](https://render.com/docs)
- [Vercel Documentation](https://vercel.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Checklist Pre-Despliegue](./CHECKLIST_PRE_DESPLIEGUE.md)

