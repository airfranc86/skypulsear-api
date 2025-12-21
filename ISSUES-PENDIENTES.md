# Issues Pendientes - SkyPulse

**Última actualización:** 2025-12-21  
**Estado:** Investigación Pendiente

---

## 🔴 Problema Crítico: Meteosource API no funciona en Render

### Descripción del Problema

La API de Meteosource (plan gratuito) no está funcionando cuando se despliega en Render. El error específico es:

```
Failed to resolve 'api.meteosource.com' ([Errno -2] Name or service not known)
```

### Contexto

- **API Key:** ✅ Configurada correctamente (`METEOSOURCE_API_KEY`)
- **Plan:** Gratuito (Free tier)
- **Endpoint:** `https://api.meteosource.com/v1/flexi/point`
- **Parámetros:** Correctos según documentación (`lang` en lugar de `language`)
- **Retry Logic:** Implementado con backoff exponencial (3 intentos)
- **Timeout:** 30 segundos

### Comportamiento Observado

1. **Localmente:** Funciona correctamente (si se prueba)
2. **En Render:** Falla con error DNS persistente después de 3 intentos
3. **Otros servicios:** Windy-GFS funciona correctamente en el mismo entorno

### Hipótesis

1. **Restricciones de red en Render Free Tier:**
   - El plan gratuito de Render podría tener restricciones de DNS/resolución de nombres
   - Posible bloqueo de ciertos dominios externos

2. **Problema temporal de DNS:**
   - Aunque el retry debería ayudar, el problema persiste
   - No es un problema intermitente, es consistente

3. **Configuración de red faltante:**
   - Podría requerir configuración adicional en Render
   - Posible necesidad de actualizar a plan de pago

4. **Problema con el dominio de Meteosource:**
   - El dominio `api.meteosource.com` podría tener problemas de DNS
   - Verificar si el dominio está accesible desde otros servicios

### Acciones Requeridas

- [ ] **Verificar restricciones de red en Render Free Tier**
  - Revisar documentación de Render sobre limitaciones del plan gratuito
  - Contactar soporte de Render si es necesario

- [ ] **Probar desde otro servicio de hosting**
  - Desplegar temporalmente en otro proveedor (Railway, Fly.io, etc.)
  - Verificar si el problema es específico de Render

- [ ] **Verificar accesibilidad del dominio Meteosource**
  - Probar resolución DNS desde diferentes ubicaciones
  - Verificar si hay problemas conocidos con el dominio

- [ ] **Contactar soporte de Meteosource**
  - Verificar si hay restricciones para el plan gratuito
  - Preguntar sobre problemas conocidos con resolución DNS

- [ ] **Considerar alternativas**
  - Usar Windy-GFS como fuente principal (ya funciona)
  - Evaluar otros proveedores de datos meteorológicos

### Estado Actual

- **Workaround:** Windy-GFS está funcionando correctamente y se usa como fuente principal
- **Impacto:** Bajo - El sistema funciona con Windy-GFS, pero se pierde la diversidad de fuentes
- **Prioridad:** Media - No bloquea el funcionamiento, pero limita la robustez del sistema

### Referencias

- Documentación Meteosource: https://www.meteosource.com/es/client/interactive-documentation
- Repositorio: `app/data/repositories/meteosource_repository.py`
- Logs de error: Render Dashboard → Logs

---

## ⚠️ Windy-CAMS Removido

### Decisión

Windy-CAMS fue removido del sistema porque no retorna datos para la región de Córdoba, Argentina.

### Estado

- **Modelo:** CAMS (Copernicus Atmosphere Monitoring Service)
- **Razón de remoción:** No retorna datos válidos para las coordenadas de prueba
- **Alternativa:** Solo se usa Windy-GFS, que funciona correctamente

### Notas

- CAMS podría funcionar en otras regiones
- Si se necesita en el futuro, se puede reactivar con mejor manejo de errores

---

## 📝 Notas Adicionales

### Fuentes de Datos Activas

1. **Windy-GFS** ✅
   - Funcionando correctamente
   - Modelo global con actualizaciones frecuentes
   - Fuente principal actual

2. **Meteosource** ❌
   - Bloqueado por problema DNS en Render
   - Requiere investigación (ver sección arriba)

3. **Estaciones Locales** ⚠️
   - CSV no disponible en Render (normal)
   - Funciona localmente si el archivo está presente

4. **WRF-SMN** ⚠️
   - Depende de Meteosource como fallback
   - Requiere Meteosource funcionando o acceso directo a AWS S3

---

**Mantener este documento actualizado con cualquier progreso en la investigación.**

