# SkyPulse - Sistema de Alertas Meteorológicas para Argentina

API de decisiones meteorológicas para Argentina. Backend FastAPI desplegado en Render, Frontend desplegado en Vercel.

> 📍 **Lanzamiento inicial:** Datos para Córdoba, Argentina  
> 🗓️ **Última actualización:** 2026-01-04  
> 🌐 **URL Producción:** https://skypulse-ar.vercel.app/dashboard

---

## 📚 Índice

1. [Stack Tecnológico](#stack-tecnológico)
2. [Arquitectura](#arquitectura)
3. [Scoring de Riesgo (0-5)](#scoring-de-riesgo-0-5)
4. [Sistema de Alertas](#sistema-de-alertas)
5. [Frontend-Only Mode](#frontend-only-mode)
6. [Endpoints API](#endpoints-api)
7. [Desarrollo Local](#desarrollo-local)
8. [Deploy](#deploy)
9. [Configuración](#configuración)
10. [Problemas Conocidos](#problemas-conocidos)
11. [Revisión UI y Consistencia](#revisión-ui-y-consistencia)

---

## 🛠️ Stack Tecnológico

### Backend
- **Framework:** FastAPI
- **Runtime:** Python 3.12+
- **Deploy:** Render
- **Database:** Supabase (PostgreSQL) - Pendiente integración

### Frontend
- **Framework:** Vanilla JavaScript + HTML5
- **Deploy:** Vercel
- **APIs:** Meteosource, Open-Meteo, Windy Embed
- **Visualización:** Chart.js, Plotly
- **Animaciones:** anime.js (timeline para secuencias complejas)

### Fuentes de Datos Meteorológicos
- **Open-Meteo:** Fuente principal (gratuito, sin API key)
  - Modelos: ECMWF (europeo) y GFS (global)
  - **NOTA:** No es ideal para Córdoba, Argentina, pero es la solución temporal hasta configurar NetCDF para WRF-SMN
- **Windy-GFS:** Fallback automático (requiere API key opcional)
- **Meteosource:** Opcional para alertas (si está configurado)
- **WRF-SMN:** Pendiente integración desde AWS S3 (Open Data, gratuito, 4km resolución)
- **Estaciones Locales:** CSV (solo local)

---

## 🏗️ Arquitectura

### Estado Actual (2026-01-04)

- ✅ **Frontend activo:** https://skypulse-ar.vercel.app/dashboard
- ⏸️ **Backend pausado:** Temporalmente por fallas con Render y Meteosource
- ✅ **Lógica de alertas:** Operativa (scoring 0-5, niveles 0-4)
- ✅ **Arquitectura:** Frontend-only con Open-Meteo (principal) + Windy (fallback) + AlertEngine
- ✅ **Open-Meteo implementado:** Cliente con fallback automático a Windy
- ⏳ **WRF-SMN:** Pendiente configuración NetCDF para integración desde AWS S3

### Estructura del Proyecto

```
SkyPulse/
├── app/                    # Backend FastAPI
│   ├── api/               # Endpoints y routers
│   ├── data/              # Repositorios y schemas
│   ├── services/           # Lógica de negocio
│   │   ├── risk_scoring.py      # Scoring 0-5
│   │   ├── alert_service.py     # Alertas 0-4
│   │   └── pattern_detector.py  # Detección de patrones
│   └── utils/             # Utilidades
├── public/                # Frontend
│   ├── dashboard.html     # Panel principal
│   ├── aviacion-demo.html # Panel de aviación
│   ├── js/
│   │   └── anime-utils.js # Utilidades de animación con anime.js timeline
│   ├── alert-engine.js    # Motor de alertas frontend
│   ├── alert-rules.json   # Reglas de alertas
│   ├── open-meteo-client.js # Cliente Open-Meteo (principal) con fallback Windy
│   └── meteosource-client.js # Cliente Meteosource (opcional, para alertas)
├── tests/                 # Tests del backend
└── requirements.txt       # Dependencias Python
```

---

## 📊 Scoring de Riesgo (0-5)

### Definición

El sistema calcula un **score de riesgo de 0 a 5** (con 1 decimal) basado en múltiples factores meteorológicos.

**Ubicación Backend:** `app/services/risk_scoring.py`

```python
class RiskScore(BaseModel):
    score: float = Field(ge=0, le=5)  # Escala 0-5
```

### Cálculo del Scoring

1. **Riesgos individuales** (0-100):
   - Temperatura, Viento, Precipitación
   - Tormentas, Granizo, Patrones detectados

2. **Score ponderado** según perfil de usuario:
   - Cada perfil tiene pesos diferentes (ej: Aviación prioriza viento 0.4)

3. **Score combinado**:
   - 60% promedio ponderado + 40% máximo individual

4. **Conversión a escala 0-5**:
   ```python
   final_score = min(5.0, round((combined_score / 100) * 5, 1))
   ```

### Mapeo Scoring → Categorías

| Scoring | Categoría | Equivalente Alerta |
|---------|-----------|-------------------|
| 0.0-0.9 | VERY_LOW | NORMAL (0) |
| 1.0-1.9 | LOW | ATTENTION (1) |
| 2.0-2.9 | MODERATE | CAUTION (2) |
| 3.0-3.9 | VERY_HIGH | ALERT (3) |
| 4.0-5.0 | EXTREME | CRITICAL (4) |

**Nota importante:** Scoring 5.0 se mapea a EXTREME (equivalente a alerta CRITICAL nivel 4). Esto es **correcto y consistente**.

---

## 🚨 Sistema de Alertas

### Niveles de Alerta (0-4)

**Ubicación Backend:** `app/services/alert_service.py`

```python
class AlertLevel(IntEnum):
    NORMAL = 0      # Condición Normal
    ATTENTION = 1   # Atención
    CAUTION = 2     # Precaución
    ALERT = 3       # Alerta
    CRITICAL = 4    # Alerta Crítica
```

### Ventanas Temporales

- **0-3h:** Próximas 0-3 horas (más crítico)
- **3-12h:** Próximas 3-12 horas
- **12-24h:** Próximas 12-24 horas
- **24-48h:** Próximas 24-48 horas

### Umbrales de Alertas

| Fenómeno | Umbral | Nivel por Ventana |
|----------|--------|-------------------|
| Precipitación intensa | ≥30mm | 0-3h: 4, 3-12h: 3, 12-24h: 2, 24-48h: 1 |
| Vientos fuertes | ≥20 m/s | 0-3h: 3, 3-12h: 2, 12-24h: 1 |
| Calor extremo | ≥40°C | 0-3h: 3, 3-12h: 3, 12-24h: 2 |
| Heladas | ≤0°C | 0-3h: 3, 3-12h: 3, 12-24h: 2 |
| Tormenta convectiva | precip≥15mm + viento≥15 m/s | 0-3h: 4, 3-12h: 3, 12-24h: 2 |

---

## 🎯 Frontend-Only Mode

### Descripción

El sistema puede operar **completamente sin backend** usando:

1. **Open-Meteo API** (principal, gratuito, sin API key)
2. **Windy API** (fallback automático si Open-Meteo falla, requiere API key opcional)
3. **Meteosource API** (opcional, para alertas si está configurado)
4. **AlertEngine** (evaluación de reglas en JavaScript)
5. **alert-rules.json** (reglas declarativas)

### Archivos Clave

- **`public/open-meteo-client.js`:** Cliente Open-Meteo con fallback automático a Windy
- **`public/alert-rules.json`:** Reglas declarativas de alertas
- **`public/alert-engine.js`:** Motor de evaluación de alertas
- **`public/meteosource-client.js`:** Cliente Meteosource (opcional, para alertas)

### Configuración de API Key

**Opción 1: Variable de Entorno en Vercel (Recomendado)**

1. Vercel Dashboard → Settings → Environment Variables
2. Agregar: `METEOSOURCE_API_KEY` = tu API key
3. Configurar en `vercel.json` para inyectar como `window.METEOSOURCE_API_KEY`

**Opción 2: Hardcodeada en dashboard.html (Solo desarrollo)**

```javascript
const CONFIG = {
    meteosourceApiKey: 'tu_api_key_aqui' // ⚠️ SOLO PARA DESARROLLO
};
```

### Flujo de Datos Frontend-Only

```
1. Usuario carga dashboard.html
   ↓
2. Carga alert-rules.json y inicializa AlertEngine
   ↓
3. Inicializa OpenMeteoClient (principal) con fallback Windy opcional
   ↓
4. Inicializa MeteosourceClient (opcional, para alertas)
   ↓
5. fetchWeatherData() es llamado:
   a. Intenta obtener datos de Open-Meteo (ECMWF o GFS)
   b. Si falla, usa Windy como fallback (si está configurado)
   c. Si ambos fallan, usa cache o datos de ejemplo
   ↓
6. fetchAlerts() es llamado:
   a. Prioridad: Meteosource > Open-Meteo
   b. Obtiene pronóstico horario de la fuente disponible
   c. AlertEngine evalúa reglas contra pronóstico
   d. Genera alertas con niveles, fenómenos, recomendaciones
   ↓
7. Datos y alertas se muestran en UI (dashboard, alert-banner, alert-stack)
```

---

## 📡 Endpoints API

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/health` | Health check | No |
| GET | `/api/v1/weather/current` | Datos actuales fusionados | No |
| GET | `/api/v1/weather/forecast` | Pronóstico multi-modelo | No |
| POST | `/api/v1/risk-score` | Cálculo de riesgo por perfil | Opcional |
| GET | `/api/v1/alerts` | Alertas meteorológicas | No |
| GET | `/api/v1/patterns` | Patrones argentinos detectados | No |
| GET | `/docs` | Swagger UI | No |

### Perfiles Disponibles

- `piloto` - Aviación general
- `agricultor` - Agricultura y ganadería
- `camionero` - Transporte terrestre
- `deporte_aire_libre` - Deportes al aire libre
- `evento_exterior` - Eventos al aire libre
- `construccion` - Construcción
- `turismo` - Turismo / Excursión
- `general` - General

---

## 💻 Desarrollo Local

### Backend

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

### Frontend

```bash
cd public
python -m http.server 8080
# Abrir http://localhost:8080
```

---

## 🚀 Deploy

### Backend (Render)

1. Push a GitHub
2. Conectar repo en Render
3. Render detecta `render.yaml` automáticamente
4. Configurar variables de entorno en Render Dashboard
5. Deploy

**URL Backend:** https://skypulsear-api.onrender.com

### Frontend (Vercel)

```bash
# Instalar Vercel CLI (si no está instalado)
npm i -g vercel

# Login en Vercel
vercel login

# ⚠️ IMPORTANTE: Desplegar desde la carpeta public/
cd public

# Desplegar a producción
vercel --prod --yes
```

**⚠️ NOTA CRÍTICA:** El despliegue DEBE hacerse desde `public/`, no desde la raíz. Si se despliega desde la raíz, Vercel detectará FastAPI y fallará.

**Estado del Despliegue (2026-01-04):**
- ✅ Configuración correcta: `vercel.json` en raíz con `outputDirectory: "public"`
- ✅ Despliegue exitoso desde `public/`
- ✅ URL funcionando: https://skypulse-ar.vercel.app/dashboard

**URL Frontend:** https://skypulse-ar.vercel.app/dashboard  
**Proyecto Vercel:** `skypulse-ar`  
**Dashboard Vercel:** https://vercel.com/franc-projects/skypulse-ar

---

## ⚙️ Configuración

### Variables de Entorno (Render)

#### Variables Requeridas

**1. METEOSOURCE_API_KEY**
```
Key: METEOSOURCE_API_KEY
Value: [Tu API key de Meteosource]
```
- Obtener en: https://www.meteosource.com/client/signup

**2. VALID_API_KEYS** (Para autenticación)
```
Key: VALID_API_KEYS
Value: sk_live_abc123,sk_test_xyz789
```
- **Formato**: Separadas por comas (sin espacios)
- **Ejemplo**: `sk_live_abc123def456,sk_test_xyz789uvw012`

**3. PYTHON_VERSION**
```
Key: PYTHON_VERSION
Value: 3.12
```

#### Variables para Supabase (Cuando se integre)

**4. SUPABASE_URL**
```
Key: SUPABASE_URL
Value: https://tu-proyecto.supabase.co
```

**5. SUPABASE_KEY**
```
Key: SUPABASE_KEY
Value: [Tu anon/public key de Supabase]
```

### Configuración Frontend (Vercel)

**Proyecto:** `skypulse-ar`  
**URL Producción:** https://skypulse-ar.vercel.app/dashboard  
**Dashboard Vercel:** https://vercel.com/franc-projects/skypulse-ar

**Variables de Entorno Opcionales en Vercel:**
- `WINDY_API_KEY` - Para fallback automático si Open-Meteo falla
- `METEOSOURCE_API_KEY` - Para alertas (si no está configurado, usa Open-Meteo)

En `dashboard.html`, la configuración está en:

```javascript
const CONFIG = {
    backendUrl: 'https://skypulsear-api.onrender.com', // Backend pausado
    apiKey: null,  // Opcional, para features premium
    windyApiKey: null,  // Opcional: Para fallback si Open-Meteo falla
    meteosourceApiKey: null  // Opcional: Para alertas (se obtiene de window.METEOSOURCE_API_KEY)
};
```

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

## 🐛 Problemas Conocidos

### 🔴 Meteosource API no funciona en Render

**Problema:** La API de Meteosource (plan gratuito) no funciona cuando se despliega en Render.

**Error:**
```
Failed to resolve 'api.meteosource.com' ([Errno -2] Name or service not known)
```

**Estado Actual (2026-01-04):**
- ⏸️ **Backend pausado** temporalmente por este problema
- ✅ **Frontend funciona** con Open-Meteo como fuente principal (gratuito, sin API key)
- ✅ **Fallback implementado:** Windy-GFS como fallback automático si Open-Meteo falla
- ✅ **Meteosource:** Opcional para alertas, si no está disponible usa Open-Meteo

**Hipótesis:**
1. Restricciones de red en Render Free Tier
2. Problema temporal de DNS
3. Configuración de red faltante

**Acciones Realizadas (2026-01-04):**
- [x] Implementado Open-Meteo como fuente principal (gratuito, sin API key)
- [x] Implementado fallback automático a Windy si Open-Meteo falla
- [x] Alertas funcionan con Open-Meteo si Meteosource no está disponible
- [ ] Pendiente: Configurar NetCDF para WRF-SMN (solución ideal para Córdoba)

### ⚠️ Windy-CAMS Removido

Windy-CAMS fue removido porque no retorna datos para la región de Córdoba, Argentina.

**Estado:**
- **Modelo:** CAMS (Copernicus Atmosphere Monitoring Service)
- **Razón:** No retorna datos válidos para las coordenadas de prueba
- **Alternativa:** Solo se usa Windy-GFS, que funciona correctamente

---

## 🎨 Revisión UI y Consistencia

### Estado General

**✅ Fortalezas:**
- La UI respeta correctamente el scoring 0-5
- La lógica de alertas está bien implementada
- El código está preparado para integración backend
- La estructura visual es clara y consistente

**⚠️ Áreas de Mejora:**
- Documentación de mapeos y relaciones
- Validación de datos del backend
- Clarificación de jerarquía visual

### Problemas Identificados

#### C-1: Discrepancia Scoring (0-5) vs Alertas (0-4) - RESUELTO

**Backend:** ✅ **CORRECTO**
- Scoring 0-5 implementado correctamente
- Alertas 0-4 implementadas correctamente
- Mapeo scoring → categorías correcto
- **No requiere cambios**

**Frontend:** ⚠️ **INCONSISTENTE**
- `alert-rules.json` solo define niveles 0-4
- Necesita manejar scoring 5 del backend
- **Recomendación:** Mapear scoring 5 → alerta nivel 4 (CRITICAL)

#### M-1: Jerarquía Visual Confusa

**Problema:** Alert banner (0-4) y risk score card (0-5) compiten por atención.

**Recomendación:** Agregar tooltip que explique la relación entre alert level (0-4) y risk score (0-5).

#### C-2: Panel de Aviación Separado

**Estado:** El panel de Aviación es una página separada (`aviacion-demo.html`), no está integrado en el dashboard principal.

**Impacto:** No afecta funcionalidad actual, pero puede confundir UX.

---

## 🎯 Tareas Prioritarias

### 🔴 PRIORIDAD CRÍTICA - 2025-12-22

#### Implementar WRF-SMN desde AWS S3 para Alertas de Riesgo por Tormenta

**Objetivo:** Integrar acceso directo a WRF-SMN desde AWS S3 (Open Data, gratuito) para mejorar precisión en detección de tormentas severas.

**Contexto:**
- Backend pausado temporalmente - migrando a WRF-SMN desde AWS S3
- WRF-SMN es el modelo ideal para alertas de riesgo por tormenta:
  - ✅ **Gratuito** - AWS Open Data (bucket `smn-ar-wrf`)
  - ✅ **Alta resolución** - 4 km (superior a ECMWF ~14 km y GFS ~27 km)
  - ✅ **Ideal para tormentas** - Convección explícita, topografía local (Sierras de Córdoba)
  - ✅ **Específico para Argentina** - Optimizado para región central

**Estado Actual:**
- ✅ Repositorio `WRFSMNRepository` creado (`app/data/repositories/wrfsmn_repository.py`)
- ⏳ Pendiente: Completar lectura de NetCDF desde AWS S3
- ⏳ Pendiente: Integrar datos WRF-SMN en cálculo de risk scoring frontend

**Tareas Específicas:**
1. **Completar implementación de lectura NetCDF desde S3:**
   - Agregar dependencias: `netCDF4`, `xarray`, `s3fs` (opcional)
   - Implementar función `_get_from_s3()` completa (ver documentación en líneas 272-363)
   - Implementar función `_extract_weather_from_netcdf()` para extraer datos por coordenadas

2. **Crear cliente JavaScript para WRF-SMN (frontend):**
   - Cliente para acceder a AWS S3 desde frontend (usando AWS SDK o API Gateway)
   - O crear endpoint proxy en backend (cuando se reactive)
   - Alternativa: Usar servicio intermedio (Lambda, Cloudflare Workers)

3. **Integrar WRF-SMN en cálculo de risk scoring:**
   - Actualizar `calculateRisks()` en `dashboard.html` para usar datos WRF-SMN
   - Priorizar WRF-SMN para detección de tormentas (weather codes 95-99)
   - Mejorar detección de granizo con datos de alta resolución

**Referencias:**
- Documentación AWS: https://registry.opendata.aws/smn-ar-wrf-dataset/
- Estructura archivos: https://odp-aws-smn.github.io/documentation_wrf_det/
- Código existente: `app/data/repositories/wrfsmn_repository.py` (líneas 272-363)

**Nota:** NO usar GFS ni Meteoblue. WRF-SMN es la opción gratuita recomendada.

---

## 📝 Próximos Pasos

### Inmediato (2025-12-22)
1. 🔴 **Implementar WRF-SMN desde AWS S3** (ver sección Tareas Prioritarias arriba)
2. Documentar mapeo scoring → categorías en código
3. Agregar validación de rango de scoring en frontend
4. Mapear scoring 5 → alerta nivel 4 en `alert-engine.js`

### Corto Plazo
1. Resolver problema de Meteosource en Render
2. Evaluar integración panel de Aviación
3. Agregar tooltips explicativos en UI

### Largo Plazo
1. Integrar Supabase para autenticación JWT
2. Migrar rate limiting a Redis para producción
3. Agregar logging y métricas
4. Testing end-to-end en producción

---

## 📚 Referencias

- **Meteosource API:** https://www.meteosource.com/client/signup
- **Windy API:** https://api.windy.com/api-key
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Vercel Docs:** https://vercel.com/docs
- **Render Docs:** https://render.com/docs

---

## 📄 Licencia

Propietario - Francisco A.

---

**Última actualización:** 2026-01-04  
**Versión Backend:** Pausado temporalmente  
**Versión Frontend:** v2.2 - Activa (Frontend-Only Mode con Open-Meteo + Windy fallback)

## 📋 Estado del Proyecto (2026-01-04)

### ✅ Completado Recientemente

- [x] **Open-Meteo implementado** como fuente principal de datos meteorológicos
- [x] **Fallback automático a Windy** si Open-Meteo falla
- [x] **Cliente Open-Meteo** con soporte para modelos ECMWF y GFS
- [x] **Alertas funcionan con Open-Meteo** si Meteosource no está disponible
- [x] **Despliegue desde `public/`** configurado y funcionando
- [x] **Documentación actualizada** con estado actual del proyecto

### ⏳ Pendiente

- [ ] **Configurar NetCDF** para procesar WRF-SMN desde AWS S3
- [ ] **Integrar WRF-SMN** como fuente principal (reemplazar Open-Meteo)
- [ ] **Resolver problema Meteosource** en Render (backend)
- [ ] **Reactivar backend** cuando WRF-SMN esté integrado

### 📝 Notas Importantes

- **Open-Meteo no es ideal para Córdoba, Argentina**, pero es la solución temporal hasta configurar NetCDF para WRF-SMN
- **WRF-SMN** (4km resolución) es la solución ideal, pero requiere procesamiento de NetCDF
- **Backend pausado** temporalmente, todo funciona en frontend-only mode
