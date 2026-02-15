# SkyPulse Web

Frontend estático del sistema meteorológico SkyPulse: dashboard, páginas informativas y cliente API. Desplegable en Vercel u otro host de estáticos.

**Última actualización:** 2026-02-15  

**Auditoría de consistencia:** 2026-02-15 — Conversión m/s → km/h para viento; uso de `wind_direction_deg` cuando la API lo envía; risk sub-scores en 0–5 desde backend. Ver `docs/AUDITORIA_CONSISTENCIA_FRONTEND_BACKEND.md`.

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

### Mapeo y unidades (consistencia con la API)

- **Viento:** La API devuelve **`wind_speed_kmh`** en current y en cada ítem de forecast; el dashboard usa esos valores en todo el sistema (métricas, riesgo, timeline). Si la API no envía `wind_speed_kmh`, se usa `wind_speed` (m/s) × 3.6. Open-Meteo (fallback) se convierte localmente a km/h.
- **Dirección del viento:** Se usa `wind_direction_10m` en grados (0–360) si la API envía `wind_direction_deg`; si no, se usa el cardinal (`wind_direction`, ej. "S"). La etiqueta y el color por dirección son coherentes cuando el backend envía grados.
- **Risk:** El backend devuelve `score` (0–5) y sub-scores en 0–5. El frontend multiplica los sub-scores por 20 para las barras 0–100.
- **Campos de current:** Se normalizan a `temperature_2m`, `apparent_temperature`, `relative_humidity_2m`, `wind_speed_10m`, `wind_direction_10m`, `precipitation`, `cloud_cover`, `weather_code`, `surface_pressure`, `time` según contrato en [AUDITORIA_CONSISTENCIA_FRONTEND_BACKEND.md](../../docs/AUDITORIA_CONSISTENCIA_FRONTEND_BACKEND.md).

---

## Build y ejecución local (terminal)

Desde la carpeta **`apps/web`**:

```bash
# Instalar dependencias (solo la primera vez; incluye servidor estático para dev)
pnpm install

# Previsualizar el frontend (servidor en http://localhost:3000)
pnpm run dev
# o
pnpm start
```

Luego abre en el navegador: **http://localhost:3000** (redirige a dashboard) o **http://localhost:3000/dashboard.html**.

```bash
# "Build" (frontend estático: no hay compilación; el script solo informa)
pnpm run build
```

**Resumen:**

| Comando        | Descripción                                      |
|----------------|--------------------------------------------------|
| `pnpm install` | Instala dependencias (ej. `serve` para dev).    |
| `pnpm run dev` | Sirve la carpeta en http://localhost:3000.       |
| `pnpm start`   | Igual que `dev` (alias).                         |
| `pnpm run build` | No hace build real; solo mensaje informativo.  |

Para que la API local funcione sin CORS, el backend debe estar en marcha (p. ej. en otro puerto) y `CONFIG.backendUrl` apuntando a esa URL.

---

## Despliegue (Vercel)

- Proyecto estático; `pnpm run dev` / `pnpm start` sirven la carpeta localmente (ver sección anterior).
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
