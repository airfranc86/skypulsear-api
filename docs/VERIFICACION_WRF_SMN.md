# Verificación de uso de datos WRF-SMN

Comprobar que el backend está devolviendo datos fusionados **Windy + WRF-SMN** cuando `WRF_SMN_ENABLED=true`.

## 1. Comprobar respuesta del backend

Desde terminal (sustituir `TU_API_KEY` por una clave en `VALID_API_KEYS`):

```bash
curl -s -H "X-API-Key: TU_API_KEY" "https://skypulsear-api.onrender.com/api/v1/weather/current?lat=-31.42&lon=-64.19"
```

**Qué revisar:**

- `"source": "fused"` — la respuesta es del motor de fusión.
- `"meteo_source_display"` — debe contener **"WRF-SMN"** o **"Windy GFS, WRF-SMN"** si WRF está habilitado y aportó datos. Si solo aparece "Windy GFS", WRF no contribuyó (circuit abierto, archivo no encontrado en S3, o `WRF_SMN_ENABLED=false`).

Ejemplo de salida esperada cuando WRF participa:

```json
{
  "current": { "temperature": 22, "wind_speed_kmh": 10, ... },
  "source": "fused",
  "meteo_source_display": "Windy GFS, WRF-SMN"
}
```

## 2. Por qué el dashboard puede seguir mostrando Open-Meteo

Si en el navegador ves **"Risk score calculado desde datos Open-Meteo"** y **"Meteosource no configurado"**:

1. **El frontend está usando el fallback Open-Meteo** porque la petición al backend falló (timeout, 401, CORS, 503).
2. **"Meteosource"** en ese mensaje se refiere al cliente Meteosource del frontend (opcional para alertas), no a WRF-SMN. WRF-SMN se usa solo en el **backend** (fusión Windy + WRF).

**Pasos útiles:**

- **Pestaña Network (F12):** Ver si existe petición a `skypulsear-api.onrender.com/api/v1/weather/current`. Revisar estado (200, 401, 504) y tiempo de respuesta (cold start en Render puede superar 20 s).
- **Consola:** Si aparece `[Backend] ⚠️ Error obteniendo datos del backend`, el backend no devolvió datos correctamente; el frontend usa entonces Open-Meteo.
- **Fuente preferida:** En el selector del dashboard, elegir **"Windy + WRF"** (o equivalente) para forzar uso del backend; si está en "Open-Meteo", el frontend no llamará al backend para tiempo/riesgo.

## 3. Resumen

| Dónde | Qué comprobar |
|-------|----------------|
| **Backend (Render)** | Variable `WRF_SMN_ENABLED=true` en Environment. |
| **Respuesta API** | `meteo_source_display` contiene "WRF-SMN" cuando WRF aporta datos. |
| **Frontend** | Fuente "Windy + WRF" seleccionada; en Network, request a `/api/v1/weather/current` con 200. |
| **Consola** | No debe aparecer fallback a Open-Meteo si quieres datos Windy+WRF. |

Si el backend responde 200 con `meteo_source_display` incluyendo "WRF-SMN", los datos WRF-SMN se están tomando correctamente en la fusión. Si el dashboard sigue mostrando Open-Meteo, el problema es de conexión frontend–backend (timeout, 401, CORS o fuente seleccionada en UI).

## 4. Debugger se pausa al cambiar la fuente de datos

Si al cambiar la fuente meteorológica (selector "Automático" / "Windy + WRF" / "Open-Meteo") el depurador de Chrome/Edge se detiene con **"Paused on exception"** (p. ej. `TypeError: Array.prototype.reduce`):

1. **Causa habitual:** En DevTools → **Sources** → panel **Breakpoints** están activas **"Pause on uncaught exceptions"** o **"Pause on caught exceptions"**. Cualquier excepción (incluso en extensiones) pausa la ejecución.
2. **Comprobar el archivo:** Si la pila de llamadas apunta a `content-script-start.js` o a un archivo que no es del proyecto (p. ej. de una extensión), la excepción es de la extensión, no del dashboard.
3. **Qué hacer:** Desmarcar **"Pause on caught exceptions"** (y opcionalmente "Pause on uncaught exceptions" cuando no estés depurando). El frontend ya normaliza `forecast.forecast` y `hourlyForecast` para no llamar `.map` sobre no-array; si aun así se pausa, revisar que el archivo en la pila sea `dashboard.html` o `api-client.js` del proyecto.
