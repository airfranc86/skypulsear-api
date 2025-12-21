# Integración Backend-Frontend SkyPulse

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

## 🔧 Configuración

### Variables de Entorno (Render)

En Render Dashboard, configurar:
```
METEOSOURCE_API_KEY=tu_key
WINDY_API_KEY=tu_key
VALID_API_KEYS=sk_live_abc123,sk_test_xyz789  # Separadas por comas
SUPABASE_URL=https://tu-proyecto.supabase.co  # Cuando se integre
SUPABASE_KEY=tu_key  # Cuando se integre
```

### Frontend (Vercel)

En `dashboard.html`, la configuración está en:
```javascript
const CONFIG = {
    backendUrl: 'https://skypulsear-api.onrender.com',
    apiKey: null  // Opcional, para features premium
};
```

## 📡 Endpoints Disponibles

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/health` | Health check | No |
| GET | `/api/v1/weather/current` | Datos actuales | No |
| GET | `/api/v1/weather/forecast` | Pronóstico | No |
| POST | `/api/v1/risk-score` | Risk score | Opcional |
| GET | `/api/v1/alerts` | Alertas | No |
| GET | `/api/v1/patterns` | Patrones | No |
| GET | `/docs` | Swagger UI | No |

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

## 🚀 Próximos Pasos

1. **Probar integración**: Verificar que el dashboard consume la API correctamente
2. **Integrar Supabase**: Cuando esté listo, agregar autenticación JWT
3. **Rate limiting avanzado**: Migrar a Redis para producción
4. **Monitoreo**: Agregar logging y métricas

## 📝 Notas

- El rate limiting actual usa memoria (no persistente)
- Para producción, considerar Redis para rate limiting distribuido
- Las API keys se validan contra `VALID_API_KEYS` (variable de entorno)
- En el futuro, las API keys vendrán de Supabase

