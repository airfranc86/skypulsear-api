# Diagnóstico raíz: 401, 503 y timeout en producción

**Contexto:** API FastAPI en Render (free), frontend estático en Vercel.  
**Objetivo:** Causa raíz por error, evidencia de código, cambios mínimos, prioridad e impacto.

---

## 1. Error 401 (Unauthorized)

### Diagnóstico raíz

Hay **dos causas posibles**; la más probable en Render es la **B**.

- **A) Header no llegando al backend**  
  El frontend envía `X-API-Key`; Starlette normaliza a `x-api-key`. El código ya lee `x-api-key` primero (`dependencies.py` L48). Si Render tiene **código actualizado**, esta causa queda descartada.

- **B) `VALID_API_KEYS` vacío o sin la key del frontend en Render**  
  Si en Render la variable de entorno `VALID_API_KEYS` no está definida o no incluye exactamente la key que usa el frontend (`skypulse-wrf-smn-aws`), el backend responde 401 por “API key inválida”.

### Evidencia de código

**Backend – lectura de API key (correcta si el deploy está actualizado):**

```36:59:apps/api/app/api/dependencies.py
def get_api_key_from_request(request: Request) -> Optional[str]:
    # ...
    api_key = request.headers.get("x-api-key")
    # Si no se encuentra, intentar otras variantes
    if not api_key:
        for header_name in ["X-API-Key", "X-Api-Key", "X-API-KEY"]:
            api_key = request.headers.get(header_name)
```

**Backend – validación (origen del 401):**

```99:133:apps/api/app/api/dependencies.py
    valid_api_keys = _get_valid_api_keys()  # os.getenv("VALID_API_KEYS", "").split(",")
    if not valid_api_keys:
        raise HTTPException(status_code=500, ...)  # 500, no 401
    # ...
    if api_key_clean in valid_api_keys:
        return api_key_clean
    raise HTTPException(
        status_code=401,
        detail="API key inválida. Proporcione una API key válida en el header X-API-Key.",
    )
```

**Frontend – envío de API key:**

```7:9:apps/web/js/api-client.js
    constructor(baseURL = 'https://skypulsear-api.onrender.com', apiKey = null) {
        this.baseURL = baseURL;
        this.apiKey = apiKey;
```

```3939:3940:apps/web/dashboard.html
            backendUrl: 'https://skypulsear-api.onrender.com',
            apiKey: "skypulse-wrf-smn-aws",
```

Si `CONFIG.apiKey` es `null` (p.ej. en otra build), el cliente no envía header y el backend responde 401 por “API key requerida” (L88-95 de `dependencies.py`).

### Cambios mínimos necesarios

1. **En Render (Dashboard → servicio → Environment):**  
   Añadir o corregir:
   ```bash
   VALID_API_KEYS=skypulse-wrf-smn-aws
   ```
   Sin espacios extra; si usas varias keys, separadas por coma.  
   Guardar y redeploy.

2. **Verificar código desplegado:**  
   Si el repo desplegado en Render es otro (p.ej. `skypulsear-api`), asegurarse de que ese repo tenga la versión de `get_api_key_from_request` que usa `request.headers.get("x-api-key")` (y fallbacks).

3. **Frontend:**  
   Confirmar que en producción (Vercel) se usa la build que tiene `CONFIG.apiKey = "skypulse-wrf-smn-aws"` (o la misma key que pusiste en `VALID_API_KEYS`). No desplegar la versión con `apiKey: null`.

### Prioridad e impacto

- **Prioridad:** 1 (máxima).  
- **Impacto:** Elimina 401 en `/api/v1/weather/current` y `/api/v1/weather/forecast` si la única causa es env/key.

---

## 2. Error 503 (Service Unavailable) en `/api/v1/risk-score`

### Diagnóstico raíz

El 503 sale en **dos sitios** del router de risk:

1. **Cuando `UnifiedWeatherEngine.get_unified_forecast()` devuelve lista vacía** (no hay datos de ninguna fuente).
2. **Cuando cualquier otra excepción** en el flujo se convierte en 503 genérico.

En Render (free), es muy probable que:

- No haya `WINDY_POINT_FORECAST_API_KEY` → no se crea Windy → menos fuentes.
- WRF-SMN falle por timeout o no disponible → `_fetch_all_sources` devuelve lista vacía.
- `get_unified_forecast` devuelve `[]` → en `risk.py` se lanza 503 explícito.

### Evidencia de código

**Origen del 503 “No se pudieron obtener datos meteorológicos”:**

```114:127:apps/api/app/api/routers/risk.py
        engine = UnifiedWeatherEngine()
        forecasts = engine.get_unified_forecast(
            latitude=request.lat,
            longitude=request.lon,
            hours=request.hours_ahead + 6,
        )
        if not forecasts:
            raise HTTPException(
                status_code=503,
                detail="No se pudieron obtener datos meteorológicos. Intente más tarde.",
            )
```

**Origen del 503 genérico:**

```204:214:apps/api/app/api/routers/risk.py
    except HTTPException:
        raise
    except Exception as e:
        # ...
        raise HTTPException(
            status_code=503,
            detail="Servicio temporalmente no disponible. Intente más tarde.",
        )
```

**Por qué `forecasts` puede estar vacío:**

- `UnifiedWeatherEngine._get_available_sources()` devuelve `["windy_ecmwf", "windy_gfs", "wrf_smn"]`.
- `RepositoryFactory` solo crea Windy-GFS (si hay `WINDY_POINT_FORECAST_API_KEY`) y WRF-SMN (si está disponible). No hay “Windy-ECMWF” en el factory.
- Si Windy no está configurado o falla, y WRF-SMN falla o tarda mucho, `_fetch_all_sources` devuelve `[]` → `get_unified_forecast` devuelve `[]` → 503.

### Cambios mínimos necesarios

- **Quick fix (recomendado):** Cuando `forecasts` esté vacío, **no** devolver 503; devolver **200** con un risk score por defecto (p. ej. score 0, categoría “bajo”, `fallback: true`) para que el frontend no rompa y pueda mostrar “Datos no disponibles” o similar.
- Implementación: en `risk.py`, antes del `if not forecasts: raise HTTPException(503...)`, construir una `RiskScoreResponse` por defecto y `return` esa respuesta con 200.

### Prioridad e impacto

- **Prioridad:** 2.  
- **Impacto:** Elimina 503 en risk-score cuando no hay datos; el usuario recibe 200 y puede degradar la UI con un mensaje claro.

---

## 3. Timeout > 10 segundos

### Diagnóstico raíz

- **Frontend:** `api-client.js` usa `Promise.race` con **10 s**. Si la respuesta tarda más (cold start de Render o backend lento), el cliente corta la petición y se ve como “timeout”.
- **Cold start Render (free):** El servicio se duerme tras inactividad; el primer request puede tardar **30–50 s**. 10 s no alcanzan.
- **Backend:** `UnifiedWeatherEngine` usa `ThreadPoolExecutor` y `future.result()` **sin timeout**. Si un repositorio (Windy, WRF-SMN, etc.) se cuelga, el hilo bloquea hasta el timeout de `requests` (30 s en `HTTP_TIMEOUT`). Eso puede dejar la petición colgada mucho tiempo y superar los 10 s del frontend.

### Evidencia de código

**Frontend – timeout 10 s:**

```36:49:apps/web/js/api-client.js
        const timeout = options.timeout || 10000;
        // ...
            const timeoutPromise = new Promise((_, reject) => {
                setTimeout(() => {
                    reject(new Error(`Timeout: La petición excedió ${timeout / 1000} segundos`));
                }, timeout);
            });
            const response = await Promise.race([fetchPromise, timeoutPromise]);
```

**Backend – sin timeout en futures:**

```208:224:apps/api/app/services/unified_weather_engine.py
            for future in as_completed(futures):
                source = futures[future]
                try:
                    data_list = future.result()  # Sin timeout: puede bloquear hasta 30s por repo
                    if data_list:
                        all_data.extend(data_list)
```

**Backend – timeout HTTP en repositorio (30 s):**

```52:53:apps/api/app/utils/constants.py
# Timeout para requests HTTP (segundos)
HTTP_TIMEOUT = 30
```

### Cambios mínimos necesarios

1. **Frontend:** Aumentar timeout por defecto a **25 s** (o 30 s) y, si es posible, usar `AbortController` para cancelar `fetch` al vencer el tiempo, para que el comportamiento sea predecible y se eviten fugas de lógica pendiente.
2. **Backend:** En `UnifiedWeatherEngine._fetch_all_sources` (y donde se use `future.result()` para estos fetches), usar `future.result(timeout=8)` (u otro valor &lt; 10 s) para no bloquear más de X segundos por fuente. Opcionalmente bajar `HTTP_TIMEOUT` a 8 s para que las llamadas HTTP externas no contribuyan a superar el límite del cliente.

### Prioridad e impacto

- **Prioridad:** 3.  
- **Impacto:** Menos timeouts en cold start (si el usuario espera ~25 s) y respuestas más acotadas en el backend; si una fuente se cuelga, el resto puede seguir y responder en &lt; 10 s en muchos casos.

---

## Resumen de prioridad de implementación

| Orden | Acción | Archivo / Lugar | Objetivo |
|-------|--------|-----------------|----------|
| 1 | Definir `VALID_API_KEYS=skypulse-wrf-smn-aws` en Render | Dashboard Render | Eliminar 401 |
| 2 | Devolver 200 con risk score por defecto cuando `forecasts` esté vacío | `apps/api/app/api/routers/risk.py` | Eliminar 503 en risk-score |
| 3 | Añadir `future.result(timeout=8)` en fetches paralelos | `apps/api/app/services/unified_weather_engine.py` | Evitar bloqueos largos; latencia &lt; ~8 s por fuente |
| 4 | Timeout 25 s + AbortController en cliente API | `apps/web/js/api-client.js` | Reducir timeouts en cold start |

---

## Estimación de impacto técnico

- **401:** Solo configuración en Render (y comprobar que el front no envía `apiKey: null`). Sin cambio de código backend si ya usas `x-api-key`.
- **503 risk-score:** Un solo cambio en un endpoint; respuesta estable 200 con fallback; el frontend puede seguir mostrando algo útil.
- **Timeout backend:** Cambio acotado en `unified_weather_engine.py`; puede hacer que algunas peticiones devuelvan menos fuentes si una tarda &gt; 8 s, pero evita colgar toda la request.
- **Timeout frontend:** Un solo archivo JS; mejora la tolerancia a cold start sin tocar el backend.

Con estos cambios se ataca la causa raíz de cada error y se prioriza solución inmediata en producción sin rediseño de arquitectura.

---

## Checklist inmediato (Render)

1. **Dashboard Render → tu servicio → Environment**
   - Añadir o corregir: `VALID_API_KEYS` = `skypulse-wrf-smn-aws` (sin espacios).
   - Opcional para risk-score: `WINDY_POINT_FORECAST_API_KEY` si tienes key de Windy.
   - Guardar y hacer **Manual Deploy** para aplicar env.

2. **Verificar que el código desplegado es el actual**
   - Si el repo en Render es `skypulsear-api`, debe tener `get_api_key_from_request` leyendo `x-api-key` primero (como en `apps/api/app/api/dependencies.py`).
   - Probar: `curl -H "X-API-Key: skypulse-wrf-smn-aws" https://skypulsear-api.onrender.com/api/v1/debug/api-key` → debe devolver `api_key_valid: true` si env y código están bien.
