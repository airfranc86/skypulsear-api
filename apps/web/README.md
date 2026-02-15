# SkyPulse Web

Frontend estático del sistema meteorológico SkyPulse: dashboard, páginas informativas y cliente API. Desplegable en Vercel u otro host de estáticos.

**Última actualización:** 2026-02-15

---

## Descripción

- **Dashboard** (`dashboard.html`): Tiempo actual, pronóstico, riesgo por perfil, alertas, patrones y mapa Windy. Consume la API de SkyPulse (Render) con fallback a Open-Meteo si el backend no está disponible.
- **Páginas informativas:** Fuentes y metodología, modelos y datos, contexto regional, investigación técnica.
- **Entrada:** `index.html` redirige a `dashboard.html`.

---

## Requisitos

- Navegador moderno (sin build obligatorio).
- Opcional: servidor local (Live Server, `npx serve`, etc.) para probar sin CORS.

---

## Estructura

```
apps/web/
├── index.html              # Redirección al dashboard
├── dashboard.html           # Aplicación principal (una sola página)
├── fuentes-y-metodologia.html
├── modelos-y-datos.html
├── contexto-regional.html
├── investigacion-tecnica.html
├── open-meteo-client.js     # Cliente Open-Meteo (fallback cuando API no está)
├── meteosource-client.js
├── alert-engine.js
├── js/
│   ├── api-client.js        # Cliente API SkyPulse (X-API-Key, timeout 25s)
│   └── secure-client.js     # Cliente con auth (token, logout → index.html)
├── assets/
├── package.json
├── vercel.json              # Configuración Vercel (headers, rutas)
└── README.md
```

---

## Configuración (dashboard)

En `dashboard.html`, objeto `CONFIG` (aprox. L3910):

- `backendUrl`: URL de la API (ej. `https://skypulsear-api.onrender.com`).
- `apiKey`: API key para la API SkyPulse (debe coincidir con `VALID_API_KEYS` en Render).
- `location` / `locations`: Ubicación por defecto y lista de ciudades.

La ubicación seleccionada se persiste en `localStorage` (`skypulse_location`). El cache meteorológico usa `skypulse_weather_cache` con versionado de esquema y TTL 30 min.

---

## Flujo de datos

1. Se intenta obtener datos desde la **API SkyPulse** (current + forecast, risk, alerts, patterns).
2. Si falla (401, timeout, etc.), se usa **Open-Meteo** (API gratuita, sin API key) como fallback.
3. Si también falla, se muestran datos de ejemplo.

---

## Ejecución local

- Abrir `dashboard.html` directamente en el navegador, o
- Servir la carpeta, por ejemplo:  
  `npx serve -l 3000`  
  y abrir `http://localhost:3000/dashboard.html`

Para que la API local funcione sin CORS, el backend debe estar en marcha (p. ej. en otro puerto) y `CONFIG.backendUrl` apuntando a esa URL.

---

## Despliegue (Vercel)

- Proyecto estático; build opcional (`package.json` tiene scripts de placeholder).
- `vercel.json` define headers (p. ej. cache para HTML) y rutas.
- Desplegar desde la raíz del monorepo apuntando a `apps/web` como directorio de salida, o desde `apps/web` con `vercel` y raíz de publicación adecuada.

---

## Persistencia (localStorage)

| Clave | Uso |
|-------|-----|
| `skypulse_weather_cache` | Cache de datos meteorológicos (versionado, TTL 30 min). |
| `skypulse_location` | Última ubicación seleccionada (rehidratada al cargar). |
| `theme` | Tema claro/oscuro. |
| `skypulse_token` | Token de sesión (si se usa SecureWeatherClient). |

`clearCache()` en el dashboard también elimina `skypulse_weather_cache` de `localStorage`.

---

## Licencia

Uso según el proyecto SkyPulse.
