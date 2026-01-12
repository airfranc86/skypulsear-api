# 🔍 Diagnóstico y Solución: Problema API Key en Render

**Fecha:** 2026-01-11  
**Estado:** ✅ Solución implementada, pendiente deploy en Render  
**Prioridad:** 🔴 Crítica

---

## 📋 Resumen del Problema

El frontend desplegado en Vercel está enviando correctamente la API key `skypulse-wrf-smn-aws` en el header `X-API-Key`, pero el backend en Render devuelve **401 Unauthorized**.

### Síntomas Observados

```
GET https://skypulsear-api.onrender.com/api/v1/weather/current?lat=-31.4201&lon=-64.1888 401 (Unauthorized)
```

**Frontend logs:**
```
[SkyPulseAPI] 📤 Headers enviados: {Content-Type: 'application/json', X-API-Key: 'skypulse-wrf-smn-aws'}
[SkyPulseAPI] 🔑 API key en cliente: skypulse-w...
```

**Backend logs (Render):**
```
"detail": "API key required. Add X-API-Key header."
```

---

## 🔍 Análisis del Problema

### 1. Confirmación: Frontend Funciona Correctamente ✅

- ✅ API key configurada: `skypulse-wrf-smn-aws`
- ✅ Header `X-API-Key` enviado correctamente
- ✅ Logs del browser confirman envío

### 2. Problema Identificado: Normalización de Headers en Starlette

**Root Cause:** Starlette (framework base de FastAPI) **normaliza automáticamente todos los headers a lowercase**.

- Header enviado: `X-API-Key`
- Header recibido por Starlette: `x-api-key` (normalizado)

**Código anterior (INCORRECTO):**
```python
api_key = request.headers.get("X-API-Key")  # ❌ No encuentra porque Starlette normalizó a 'x-api-key'
```

### 3. Confirmación: Render Ejecutando Código Viejo

El endpoint de diagnóstico `/api/v1/debug/api-key` devuelve **404**, confirmando que Render no ha actualizado el código con las correcciones.

---

## ✅ Solución Implementada

### Cambio en `apps/api/app/api/dependencies.py`

**Antes:**
```python
def get_api_key_from_request(request: Request) -> Optional[str]:
    # Buscaba "X-API-Key" (mayúsculas) - NO funcionaba
    api_key = request.headers.get("X-API-Key")
    # ...
```

**Después:**
```python
def get_api_key_from_request(request: Request) -> Optional[str]:
    """
    Lee API key del header de manera case-insensitive.
    
    CRÍTICO: Starlette normaliza TODOS los headers a lowercase con guiones.
    'X-API-Key' se convierte en 'x-api-key' automáticamente.
    """
    # Buscar primero la forma normalizada (más común)
    api_key = request.headers.get("x-api-key")
    
    # Si no se encuentra, intentar otras variantes (por si algún proxy no normaliza)
    if not api_key:
        for header_name in ["X-API-Key", "X-Api-Key", "X-API-KEY"]:
            api_key = request.headers.get(header_name)
            if api_key:
                break
    
    # Búsqueda exhaustiva en todos los headers (debug)
    if not api_key:
        all_headers = dict(request.headers)
        for key, value in all_headers.items():
            key_lower = key.lower()
            if "api" in key_lower and "key" in key_lower:
                api_key = value
                break
    
    return api_key.strip() if api_key else None
```

### Mejoras Adicionales

1. **CORS explícito para X-API-Key** (`apps/api/app/api/main.py`):
   ```python
   allow_headers=[
       "*",
       "X-API-Key",      # Explícito
       "x-api-key",      # Normalizado
       "Content-Type",
       "Authorization",
       "Accept",
   ],
   ```

2. **Endpoint de diagnóstico** (`apps/api/app/api/routers/health.py`):
   - `/api/v1/debug/api-key` - Muestra qué headers está recibiendo el servidor
   - No requiere autenticación
   - Útil para verificar si código nuevo está corriendo

---

## 📝 Commits Realizados

1. **`fix(backend): especificar X-API-Key explícitamente en CORS`**
   - Commit: `58a2e03`
   - Especifica `X-API-Key` explícitamente en `allow_headers`

2. **`feat(backend): agregar endpoint de diagnóstico para API key`**
   - Commit: `069109b`
   - Endpoint `/api/v1/debug/api-key` para diagnóstico

3. **`fix(backend): corregir lectura de API key - Starlette normaliza a lowercase`**
   - Commit: `dbcb883`
   - **SOLUCIÓN PRINCIPAL**: Buscar `x-api-key` primero (normalizado)

---

## 🚀 Próximos Pasos

### 1. Deploy en Render (OBLIGATORIO)

**Opción A: Auto-deploy (si está habilitado)**
- Esperar 2-5 minutos para que Render detecte el push

**Opción B: Manual Deploy (RECOMENDADO)**
1. Ir a: https://dashboard.render.com
2. Seleccionar servicio: `skypulsear-api`
3. Clic en: **"Manual Deploy"** → **"Deploy latest commit"**
4. Esperar 5-10 minutos

### 2. Verificación Post-Deploy

**Paso 1: Verificar endpoint de diagnóstico**
```bash
curl https://skypulsear-api.onrender.com/api/v1/debug/api-key
```

**Respuesta esperada:**
```json
{
  "code_version": "NUEVO",
  "api_key_received": "skypulse-w...",
  "api_key_valid": true,
  "valid_api_keys_configured": true,
  ...
}
```

**Paso 2: Probar frontend**
- Abrir: https://skypulse-ar.vercel.app/dashboard
- Verificar que no hay errores 401
- Verificar que datos meteorológicos se cargan correctamente

### 3. Logs Esperados en Render

Después del deploy, los logs deberían mostrar:
```
🔍 API key encontrada en header 'x-api-key'
🔑 Validando API key recibida: 'skypulse-w...' (longitud: 20, total válidas: 1)
✅ API key válida: skypulse-w...
```

---

## 🔧 Archivos Modificados

1. **`apps/api/app/api/dependencies.py`**
   - Función `get_api_key_from_request()` corregida
   - Busca `x-api-key` primero (normalizado por Starlette)

2. **`apps/api/app/api/main.py`**
   - CORS actualizado con `X-API-Key` explícito

3. **`apps/api/app/api/routers/health.py`**
   - Endpoint `/api/v1/debug/api-key` agregado

---

## 📚 Referencias Técnicas

### Starlette Header Normalization

- **Documentación:** https://www.starlette.io/requests/#headers
- **Comportamiento:** Todos los headers se normalizan a lowercase con guiones
- **Ejemplo:** `X-API-Key` → `x-api-key`

### FastAPI Security Dependencies

- **Documentación:** https://fastapi.tiangolo.com/advanced/security/
- **APIKeyHeader:** Puede tener problemas con normalización
- **Solución:** Leer directamente de `Request.headers` (más confiable)

---

## ⚠️ Notas Importantes

1. **Render debe actualizar el código** - No hay workaround técnico
2. **El código está listo y pusheado** - Solo falta deploy en Render
3. **El frontend funciona correctamente** - No requiere cambios
4. **El problema es de deployment, no de código**

---

## 📊 Estado Actual

| Componente | Estado | Notas |
|------------|--------|-------|
| Frontend (Vercel) | ✅ Funcionando | Envía API key correctamente |
| Código Backend | ✅ Corregido | Pusheado a GitHub |
| Deploy Render | ⏳ Pendiente | Requiere deploy manual o auto-deploy |
| Tests Locales | ✅ Pasando | Todos los tests pasan localmente |

---

## 🎯 Conclusión

El problema estaba en cómo se leía el header `X-API-Key` en el backend. Starlette normaliza automáticamente los headers a lowercase, por lo que `X-API-Key` se convierte en `x-api-key`. El código ahora busca primero la forma normalizada.

**Solución implementada y pusheada. Solo falta que Render actualice el código mediante deploy.**

---

**Última actualización:** 2026-01-11  
**Próxima acción:** Deploy en Render
