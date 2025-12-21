# Integración Backend-Frontend SkyPulse

**Última actualización:** 2025-12-21  
**Versión:** 2.0

---

## ✅ Completado

### 1. Seguridad del Backend (FastAPI)

**Middleware implementado:**
- ✅ **Rate Limiting**: 60 req/min (público), 1000 req/hora (con API key)
- ✅ **Security Headers**: X-Content-Type-Options, X-Frame-Options, HSTS, etc.
- ✅ **API Keys**: Sistema de autenticación con header `X-API-Key`
- ✅ **CORS**: Configurado para permitir frontend en Vercel

**Archivos creados:**
- `app/api/dependencies.py` - Validación de API keys
- `app/api/middleware/rate_limit.py` - Rate limiting
- `app/api/middleware/security_headers.py` - Headers de seguridad
- `app/api/main.py` - Actualizado con middlewares

### 2. Cliente API para Frontend

**Archivos creados:**
- `public/js/api-client.js` - Cliente JavaScript para consumir la API
- `public/js/api-integration-example.js` - Ejemplos de uso

**Cliente API (`SkyPulseAPI`):**
```javascript
const api = new SkyPulseAPI('https://skypulsear-api.onrender.com', apiKey);

// Métodos disponibles:
await api.getCurrentWeather(lat, lon);
await api.getForecast(lat, lon, hours);
await api.calculateRiskScore(lat, lon, profile, hoursAhead);
await api.getAlerts(lat, lon, hours);
await api.getPatterns(lat, lon, hours);
```

### 3. Integración en Dashboard

**Actualizado:**
- `public/dashboard.html` - Usa `SkyPulseAPI` en lugar de `fetch` directo
- Configuración de `backendUrl` apuntando a Render
- Funciones `fetchCurrentWeather`, `fetchForecast`, etc. actualizadas
- Fallback a cálculo local si backend no disponible
- Fallback a Open-Meteo API si backend no disponible

### 4. Correcciones de Consistencia

**Problema resuelto:** Inconsistencia entre alert-banner y risk-score-card

**Solución:**
- ✅ `generateAlert()` ahora SIEMPRE usa `risks.score` para determinar el nivel
- ✅ Alert banner y risk score card usan la misma fuente de verdad

### 5. Warnings de Deprecación Corregidos

**Pydantic V2:**
- ✅ `class Config:` → `model_config = ConfigDict(...)` (5 modelos)

**datetime.utcnow():**
- ✅ `datetime.utcnow()` → `datetime.now(UTC)` (10 ocurrencias)

**Resultado:** 0 warnings de deprecación en tests

---

## 📡 Endpoints Disponibles

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/health` | Health check | No |
| GET | `/debug/repos` | Debug repositorios | No |
| GET | `/api/v1/weather/current` | Datos actuales | No |
| GET | `/api/v1/weather/forecast` | Pronóstico | No |
| POST | `/api/v1/risk-score` | Risk score | Opcional |
| GET | `/api/v1/alerts` | Alertas | No |
| GET | `/api/v1/patterns` | Patrones | No |
| GET | `/docs` | Swagger UI | No |

---

## 🔒 Seguridad

### Rate Limiting
- **Público**: 60 requests/minuto por IP
- **Con API Key**: 1000 requests/hora

### Headers de Seguridad
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (solo HTTPS)

### API Keys
- Header: `X-API-Key: tu_api_key`
- Configurar en `VALID_API_KEYS` (separadas por comas)
- Opcional para endpoints públicos, requerida para premium

---

## 🔧 Configuración

### Variables de Entorno (Render)

Ver `CONFIGURACION-RENDER.md` para guía detallada.

Variables requeridas:
```
METEOSOURCE_API_KEY=tu_key
WINDY_POINT_FORECAST_API_KEY=tu_key
VALID_API_KEYS=sk_live_abc123,sk_test_xyz789
```

### Frontend (Vercel)

En `dashboard.html`, la configuración está en:
```javascript
const CONFIG = {
    backendUrl: 'https://skypulsear-api.onrender.com',
    apiKey: null  // Opcional, para features premium
};
```

---

## 📊 Estado Actual

### Backend
- ✅ Endpoints FastAPI implementados y testeados
- ✅ 17 tests pasando, 1 skipped (servicio no disponible - esperado)
- ✅ 0 warnings de deprecación
- ✅ Deploy en Render funcionando

### Frontend
- ✅ Integración con backend implementada
- ✅ Fallback a cálculo local si backend no disponible
- ✅ Consistencia alert-banner vs risk-score-card
- ✅ Aclaración timeline

---

## 🚀 Próximos Pasos

1. ⏳ **Integrar Supabase**: Cuando esté listo, agregar autenticación JWT
2. ⏳ **Rate limiting avanzado**: Migrar a Redis para producción
3. ⏳ **Monitoreo**: Agregar logging y métricas
4. ⏳ **Testing end-to-end**: Verificar consistencia en producción

---

## 📝 Notas

- El rate limiting actual usa memoria (no persistente)
- Para producción, considerar Redis para rate limiting distribuido
- Las API keys se validan contra `VALID_API_KEYS` (variable de entorno)
- En el futuro, las API keys vendrán de Supabase

---

**Ver también:**
- `CONFIGURACION-RENDER.md` - Configuración de variables de entorno
- `ISSUES-PENDIENTES.md` - Problemas conocidos
- `MASTER-PLAN.md` - Plan maestro completo del proyecto
