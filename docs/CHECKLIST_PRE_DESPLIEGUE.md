# ✅ Checklist Pre-Despliegue - SkyPulse v2.0.0

**Fecha:** 2025-12-30  
**Frontend:** https://skypulse-ar.vercel.app  
**Backend:** Render (FastAPI)

---

## 🔍 Pre-Despliegue: Verificaciones Locales

### 1. Tests y Calidad de Código
- [x] Tests pasando: `pytest tests/ -v`
- [x] Sin errores de importación
- [x] Cobertura de nuevas funcionalidades >80% (circuit breaker, retry, metrics)
- [ ] Verificar que no hay `print()` en código de producción
- [ ] Verificar que no hay credenciales hardcodeadas

### 2. Dependencias
- [x] `requirements.txt` actualizado con `prometheus-client>=0.19.0`
- [ ] Verificar que todas las dependencias están en `requirements.txt`
- [ ] Verificar versiones compatibles

### 3. Configuración
- [x] CORS actualizado con dominio de Vercel
- [x] Exception handlers globales configurados
- [x] Middlewares configurados (correlation ID, metrics, security, rate limit)
- [ ] Variables de entorno documentadas

---

## 🚀 Despliegue en Render

### 1. Variables de Entorno en Render

Verificar/Configurar en Render Dashboard:

#### APIs Externas
- [ ] `METEOSOURCE_API_KEY` - API key de Meteosource
- [ ] `METEOSOURCE_TIER` - Tier de suscripción (opcional)
- [ ] `WINDY_POINT_FORECAST_API_KEY` - API key de Windy
- [ ] `VALID_API_KEYS` - Lista de API keys válidas (opcional)

#### AWS (si se usa WRF-SMN)
- [ ] `AWS_ACCESS_KEY_ID` - Access key de AWS
- [ ] `AWS_SECRET_ACCESS_KEY` - Secret key de AWS
- [ ] `AWS_REGION` - Región de AWS (ej: `us-east-1`)
- [ ] `S3_BUCKET_NAME` - Nombre del bucket S3

#### Configuración de Aplicación
- [ ] `LOG_LEVEL` - Nivel de logging (default: `INFO`)
- [ ] `ENVIRONMENT` - Entorno (`production`, `staging`, `development`)

### 2. Configuración de Render Service

Verificar en `render.yaml` o Dashboard:

- [ ] **Build Command:** `pip install -r requirements.txt`
- [ ] **Start Command:** `uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
- [ ] **Python Version:** 3.12+ (verificar en Render)
- [ ] **Health Check Path:** `/health`
- [ ] **Auto-Deploy:** Habilitado para branch `main` o `master`

### 3. Verificaciones Post-Despliegue

#### Health Check
```bash
# Verificar que el servicio responde
curl https://tu-api.onrender.com/health

# Debe retornar:
# {"status": "healthy", "service": "skypulse-api"}
```

#### Endpoints Críticos
```bash
# 1. Root endpoint
curl https://tu-api.onrender.com/

# 2. Docs (Swagger)
curl https://tu-api.onrender.com/docs

# 3. Métricas
curl https://tu-api.onrender.com/metrics

# 4. Weather endpoint (test)
curl "https://tu-api.onrender.com/api/v1/weather/current?lat=-31.42&lon=-64.19"
```

#### Logs
- [ ] Verificar logs en Render Dashboard
- [ ] Verificar formato JSON estructurado
- [ ] Verificar correlation IDs en logs
- [ ] Verificar que no hay errores críticos

---

## 🔗 Integración Frontend-Backend

### 1. Actualizar URL de API en Frontend

Verificar que el frontend apunta a la URL correcta de Render:

```javascript
// En el frontend (Vercel)
const API_BASE_URL = process.env.API_BASE_URL || 'https://tu-api.onrender.com';
```

### 2. Variables de Entorno en Vercel

Configurar en Vercel Dashboard:

- [ ] `API_BASE_URL` - URL completa de la API en Render
- [ ] `NEXT_PUBLIC_API_URL` - Si usa Next.js (opcional)

### 3. CORS

- [x] Backend configurado con `https://skypulse-ar.vercel.app`
- [ ] Verificar que frontend puede hacer requests
- [ ] Verificar headers CORS en respuesta

---

## 📊 Monitoreo y Observabilidad

### 1. Prometheus (Opcional - Local)

Si quieres monitoreo local:

```bash
# Iniciar stack de monitoreo
docker-compose -f docker-compose.monitoring.yml up -d

# Acceder a:
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3001
```

### 2. Métricas en Producción

- [ ] Endpoint `/metrics` accesible
- [ ] Métricas de circuit breakers funcionando
- [ ] Métricas de HTTP requests funcionando
- [ ] Métricas de weather sources funcionando

### 3. Logs Estructurados

- [ ] Logs en formato JSON
- [ ] Correlation IDs presentes
- [ ] Contexto estructurado en logs

---

## 🧪 Testing Post-Despliegue

### 1. Tests de Integración

```bash
# Test de health
curl https://tu-api.onrender.com/health

# Test de weather (Córdoba)
curl "https://tu-api.onrender.com/api/v1/weather/current?lat=-31.42&lon=-64.19"

# Test de risk score
curl -X POST https://tu-api.onrender.com/api/v1/risk-score \
  -H "Content-Type: application/json" \
  -d '{"lat": -31.42, "lon": -64.19, "profile": "piloto", "hours_ahead": 6}'
```

### 2. Circuit Breakers

- [ ] Verificar que circuit breakers inician en estado CLOSED
- [ ] Verificar métricas de circuit breakers en `/metrics`
- [ ] (Opcional) Simular fallos para verificar que se abren correctamente

### 3. Frontend Integration

- [ ] Abrir https://skypulse-ar.vercel.app/dashboard.html
- [ ] Verificar que carga datos meteorológicos
- [ ] Verificar que muestra risk scores
- [ ] Verificar que muestra alertas
- [ ] Verificar que muestra patrones

---

## 🐛 Troubleshooting

### Problemas Comunes

#### 1. CORS Errors
**Síntoma:** Frontend no puede hacer requests  
**Solución:**
- Verificar que `https://skypulse-ar.vercel.app` está en `allow_origins`
- Verificar headers CORS en respuesta
- Verificar que `allow_credentials=True` si se usan cookies

#### 2. API Keys No Configuradas
**Síntoma:** Error 503, "No hay fuentes de datos configuradas"  
**Solución:**
- Verificar variables de entorno en Render
- Verificar que `METEOSOURCE_API_KEY` y/o `WINDY_POINT_FORECAST_API_KEY` están configuradas

#### 3. Circuit Breaker Abierto
**Síntoma:** Error 503, "Circuit breaker is OPEN"  
**Solución:**
- Verificar logs para ver por qué se abrió
- Esperar recovery timeout (60s por defecto)
- Verificar conectividad con APIs externas

#### 4. Logs No Estructurados
**Síntoma:** Logs en formato texto plano  
**Solución:**
- Verificar que `setup_logging()` se llama al inicio
- Verificar que `JSONFormatter` está configurado

---

## 📝 Notas de Despliegue

### Versión
- **Backend:** 2.0.0
- **Frontend:** (verificar versión en Vercel)

### Cambios Principales en v2.0.0
1. ✅ Logging estructurado JSON
2. ✅ Circuit breakers para resiliencia
3. ✅ Retry logic centralizado
4. ✅ Métricas Prometheus
5. ✅ Exception handlers globales
6. ✅ Correlation IDs para trazabilidad

### Rollback Plan
Si hay problemas críticos:
1. Revertir a versión anterior en Render
2. Verificar logs para identificar problema
3. Corregir y re-desplegar

---

## ✅ Sign-Off

- [ ] Todas las verificaciones completadas
- [ ] Tests pasando en producción
- [ ] Frontend funcionando correctamente
- [ ] Monitoreo configurado
- [ ] Documentación actualizada

**Desplegado por:** _______________  
**Fecha:** _______________  
**URL Producción:** https://tu-api.onrender.com  
**URL Frontend:** https://skypulse-ar.vercel.app

