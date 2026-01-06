# 🎯 Plan de Acción - SkyPulse
## Refactorización y Mejoras Prioritarias

**Fecha de Creación:** 2025-01-05  
**Última Actualización:** 2026-01-06  
**Proyecto:** SkyPulse  
**Total de Problemas:** 291 (265 calidad + 7 seguridad + 14 performance + 5 arquitectura)

---

## 📊 Resumen Ejecutivo

Este plan prioriza las acciones críticas identificadas en la auditoría, organizadas por urgencia e impacto. Se recomienda ejecutar las tareas en el orden propuesto para maximizar la seguridad y estabilidad del sistema.

### Métricas Clave
- **Problemas Críticos:** 1 (Secrets Management)
- **Problemas de Alta Severidad:** 6 (Seguridad API)
- **Problemas de Calidad:** 265 (257 uso de `print()`, 6 funciones largas, 2 sin type hints)
- **Tiempo Estimado Total:** ~45 horas

### Estado Actual (2026-01-06)
- ✅ **Backend desplegado y funcional** en Render
- ✅ **API Keys configuradas** en Render
- ✅ **Frontend mejorado** con prioridad de backend y mejor manejo de errores
- ⏳ **Pendiente:** Refactorización de código (257 `print()`, funciones largas, type hints)
- ⏳ **Pendiente:** Autenticación y autorización en API
- ⏳ **Pendiente:** Tests de seguridad
- ⏳ **Pendiente:** Optimizaciones de performance

---

## 🔴 FASE 1: CRÍTICA - Seguridad Inmediata (2-4 horas)

### 1.2. Implementar Autenticación y Autorización en API 🔒
**Prioridad:** ALTA  
**Tiempo:** 6-8 horas  
**Riesgo:** MEDIO  
**Estado:** ⏳ PENDIENTE

#### Acciones:
- [ ] **Revisar endpoints actuales** en `app/api/main.py`
- [ ] **Implementar Supabase Auth** (o alternativa):
  ```python
  # Estructura sugerida:
  # app/api/middleware/auth.py
  # app/api/middleware/rbac.py
  ```
- [ ] **Proteger TODOS los endpoints** con decoradores de autenticación
- [ ] **Implementar RBAC** (Role-Based Access Control)
- [ ] **Crear tests de autenticación**:
  - Test de acceso sin token → 401
  - Test de acceso con token inválido → 401
  - Test de acceso con token válido → 200
  - Test de acceso sin permisos → 403

#### Archivos Afectados:
- `app/api/main.py`
- `app/api/middleware/auth.py` (nuevo)
- `app/api/middleware/rbac.py` (nuevo)
- `tests/test_auth.py` (nuevo o actualizar)

---

### 1.3. Implementar Validación de Entrada (Pydantic) 🛡️
**Prioridad:** ALTA  
**Tiempo:** 2-3 horas  
**Riesgo:** BAJO  
**Estado:** ⏳ PENDIENTE

#### Acciones:
- [ ] **Crear modelos Pydantic** para todos los endpoints:
  ```python
  # app/api/schemas/weather.py
  # app/api/schemas/alerts.py
  # app/api/schemas/risk.py
  ```
- [ ] **Reemplazar parámetros simples** con modelos Pydantic
- [ ] **Validar tipos, rangos y formatos** en todos los inputs
- [ ] **Agregar validadores custom** donde sea necesario
- [ ] **Tests de validación**:
  - Test de datos válidos → 200
  - Test de datos inválidos → 422
  - Test de tipos incorrectos → 422

#### Archivos Afectados:
- `app/api/main.py`
- `app/api/schemas/` (nuevo directorio)
- `tests/test_validation.py` (nuevo)

---

## 🟠 FASE 2: ALTA - Refactorización de Calidad (8-12 horas)

### 2.1. Reemplazar `print()` por Logging 📝
**Prioridad:** ALTA  
**Tiempo:** 3-4 horas  
**Riesgo:** BAJO  
**Impacto:** 257 instancias  
**Estado:** ⏳ PENDIENTE

#### Archivos Prioritarios:
1. **`scripts/download_custom_icons.py`** (múltiples instancias)
2. **`scripts/download_weather_icons.py`**
3. **`scripts/pre_deploy_check.py`**
4. **`scripts/test_wrf_smn.py`**
5. **`scripts/pdf/generate_pdf.py`**

#### Acciones:
- [ ] **Configurar logging centralizado**:
  ```python
  # app/utils/logging_config.py (ya existe según auditoría)
  # Verificar y mejorar si es necesario
  ```
- [ ] **Reemplazar `print()` por `logger.info()`/`logger.error()`** en cada archivo
- [ ] **Usar niveles apropiados**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- [ ] **Agregar contexto** en mensajes de log (módulo, función, datos relevantes)
- [ ] **Configurar rotación de logs** para producción

#### Ejemplo de Refactorización:
```python
# ANTES:
print(f"Descargando icono: {icon_name}")

# DESPUÉS:
import logging
logger = logging.getLogger(__name__)
logger.info(f"Descargando icono: {icon_name}", extra={"icon_name": icon_name})
```

---

### 2.2. Refactorizar Funciones Largas 🔧
**Prioridad:** ALTA  
**Tiempo:** 4-6 horas  
**Riesgo:** MEDIO  
**Estado:** ⏳ PENDIENTE

#### Funciones Prioritarias:

1. **`scripts/download_custom_icons.py::download_icon`** (78 líneas)
   - [ ] Extraer lógica de descarga
   - [ ] Extraer lógica de validación
   - [ ] Extraer lógica de guardado
   - [ ] Agregar type hints

2. **`app/services/alert_service.py::_analyze_forecasts`** (60 líneas)
   - [ ] Separar análisis de datos
   - [ ] Separar generación de alertas
   - [ ] Extraer lógica de scoring

3. **`app/services/pattern_detector.py::_detect_convective_storm`** (70 líneas)
   - [ ] Separar detección de patrones
   - [ ] Extraer validación de condiciones
   - [ ] Separar cálculo de probabilidades

4. **`app/services/risk_scoring.py::calculate_risk`** (80 líneas)
   - [ ] Separar cálculo de factores
   - [ ] Extraer normalización de scores
   - [ ] Separar agregación de resultados

5. **`app/data/repositories/meteosource_repository.py::get_forecast`** (80 líneas)
   - [ ] Separar llamada API
   - [ ] Extraer transformación de datos
   - [ ] Separar manejo de errores

6. **`app/data/repositories/windy_repository.py::get_forecast`** (90 líneas)
   - [ ] Separar llamada API
   - [ ] Extraer transformación de datos
   - [ ] Separar manejo de errores

#### Principios a Aplicar:
- **Single Responsibility Principle** - Cada función una responsabilidad
- **Máximo 30-40 líneas** por función
- **Type hints completos** en todas las funciones
- **Docstrings** descriptivos

---

### 2.3. Agregar Type Hints 🏷️
**Prioridad:** MEDIA  
**Tiempo:** 2-3 horas  
**Riesgo:** BAJO  
**Estado:** ⏳ PENDIENTE

#### Archivos Prioritarios:
- `scripts/download_custom_icons.py`
- `scripts/download_weather_icons.py`
- `scripts/pre_deploy_check.py`
- `scripts/test_wrf_smn.py`
- `app/services/model_comparison.py`
- `app/data/repositories/windy_repository.py`
- `tests/test_circuit_breaker.py`
- `tests/test_metrics.py`
- `tests/test_retry.py`

#### Acciones:
- [ ] **Agregar type hints** a todas las funciones sin tipos
- [ ] **Usar `typing` module** para tipos complejos:
  ```python
  from typing import List, Dict, Optional, Union, Tuple
  ```
- [ ] **Validar con `mypy`**:
  ```bash
  mypy app/ scripts/ tests/ --ignore-missing-imports
  ```
- [ ] **Corregir errores de tipo** reportados por mypy

---

## 🟡 FASE 3: MEDIA - Mejoras de Arquitectura y Performance (10-15 horas)

### 3.1. Refactorizar Arquitectura de API 🏗️
**Prioridad:** ALTA  
**Tiempo:** 8 horas  
**Riesgo:** ALTO  
**Estado:** ⏳ PENDIENTE

#### Acciones:
- [ ] **Separar lógica de negocio** de endpoints:
  - [ ] Mover lógica a `app/services/`
  - [ ] Endpoints solo orquestan llamadas a servicios
  - [ ] Servicios manejan validación y transformación
- [ ] **Crear capa de servicios** si no existe:
  ```
  app/
    api/
      main.py (solo endpoints)
    services/
      weather_service.py
      alert_service.py
      risk_service.py
  ```
- [ ] **Implementar manejo centralizado de errores**:
  ```python
  # app/api/exceptions.py
  # app/api/error_handlers.py
  ```
- [ ] **Configurar FastAPI para producción**:
  - [ ] Deshabilitar debug mode
  - [ ] Configurar CORS apropiadamente
  - [ ] Ocultar stack traces en producción

#### Archivos Afectados:
- `app/api/main.py` (refactorizar completamente)
- `app/api/exceptions.py` (nuevo)
- `app/api/error_handlers.py` (nuevo)
- `app/services/` (reorganizar)

---

### 3.2. Implementar Rate Limiting 🚦
**Prioridad:** MEDIA  
**Tiempo:** 2-3 horas  
**Riesgo:** BAJO  
**Estado:** ⏳ PENDIENTE

#### Acciones:
- [ ] **Instalar `slowapi` o `fastapi-limiter`**:
  ```bash
  pip install slowapi
  ```
- [ ] **Configurar rate limiting** por endpoint:
  ```python
  from slowapi import Limiter, _rate_limit_exceeded_handler
  from slowapi.util import get_remote_address
  
  limiter = Limiter(key_func=get_remote_address)
  app.state.limiter = limiter
  ```
- [ ] **Aplicar límites**:
  - Endpoints públicos: 60 req/min
  - Endpoints autenticados: 120 req/min
  - Endpoints de escritura: 30 req/min
- [ ] **Tests de rate limiting**:
  - Test de límite excedido → 429
  - Test de límite respetado → 200

---

### 3.3. Optimizar Performance de Repositorios ⚡
**Prioridad:** MEDIA  
**Tiempo:** 4-6 horas  
**Riesgo:** MEDIO  
**Estado:** ⏳ PENDIENTE

#### Acciones:
- [ ] **Implementar caching** para llamadas API:
  ```python
  from functools import lru_cache
  from datetime import datetime, timedelta
  
  @lru_cache(maxsize=128)
  def get_cached_forecast(location: str, timestamp: int):
      # Cache por 5 minutos
      pass
  ```
- [ ] **Optimizar llamadas API**:
  - [ ] Agregar timeouts
  - [ ] Implementar retry con exponential backoff
  - [ ] Usar conexiones persistentes (httpx.AsyncClient)
- [ ] **Profiling de funciones críticas**:
  ```python
  import cProfile
  import pstats
  
  profiler = cProfile.Profile()
  profiler.enable()
  # código a perfilar
  profiler.disable()
  stats = pstats.Stats(profiler)
  stats.sort_stats('cumulative')
  stats.print_stats(10)
  ```

#### Archivos Prioritarios:
- `app/data/repositories/meteosource_repository.py`
- `app/data/repositories/windy_repository.py`
- `app/services/alert_service.py`
- `app/services/risk_scoring.py`

---

### 3.4. Implementar Tests de Seguridad 🧪
**Prioridad:** ALTA  
**Tiempo:** 6 horas  
**Riesgo:** BAJO  
**Estado:** ⏳ PENDIENTE

#### Acciones:
- [ ] **Crear suite de tests de seguridad**:
  ```
  tests/security/
    test_authentication.py
    test_authorization.py
    test_input_validation.py
    test_sql_injection.py
    test_xss.py
  ```
- [ ] **Tests de autenticación**:
  - [ ] Endpoints protegidos rechazan requests sin token
  - [ ] Tokens expirados son rechazados
  - [ ] Tokens inválidos son rechazados
- [ ] **Tests de autorización**:
  - [ ] Usuarios sin permisos no pueden acceder
  - [ ] RBAC funciona correctamente
- [ ] **Tests de validación**:
  - [ ] SQL injection attempts son bloqueados
  - [ ] XSS attempts son sanitizados
  - [ ] Inputs malformados son rechazados
- [ ] **Usar herramientas**:
  - `bandit` para análisis estático
  - `safety` para vulnerabilidades de dependencias

---

## 🟢 FASE 4: BAJA - Mejoras Adicionales (8-12 horas)

### 4.1. Documentación Swagger/OpenAPI 📚
**Prioridad:** MEDIA  
**Tiempo:** 2 horas  
**Riesgo:** BAJO  
**Estado:** ⏳ PENDIENTE

#### Acciones:
- [ ] **Configurar OpenAPI** en FastAPI:
  ```python
  app = FastAPI(
      title="SkyPulse API",
      description="API para sistema de alertas meteorológicas",
      version="1.0.0",
      docs_url="/docs",
      redoc_url="/redoc"
  )
  ```
- [ ] **Agregar descripciones** a todos los endpoints
- [ ] **Documentar modelos Pydantic** con ejemplos
- [ ] **Agregar tags** para organización
- [ ] **Incluir ejemplos** de requests/responses

---

### 4.2. Mejorar Manejo de Errores en PDF Generation 📄
**Prioridad:** MEDIA  
**Tiempo:** 2 horas  
**Riesgo:** BAJO  
**Estado:** ⏳ PENDIENTE

#### Acciones:
- [ ] **Validar y sanitizar** todos los inputs en `scripts/pdf/generate_pdf.py`
- [ ] **Actualizar librería de PDF** a última versión
- [ ] **Agregar validación** de contenido antes de generar
- [ ] **Implementar logging** de errores de generación
- [ ] **Tests de seguridad** para PDF generation

---

### 4.3. Optimizar Experiencia de Usuario (Streamlit) 🎨
**Prioridad:** BAJA  
**Tiempo:** 4-6 horas  
**Riesgo:** BAJO  
**Estado:** ⏳ PENDIENTE

#### Acciones:
- [ ] **Revisar estructura** de `_legacy_streamlit/`
- [ ] **Modularizar componentes** grandes
- [ ] **Agregar feedback visual** para operaciones largas
- [ ] **Mejorar manejo de errores** en UI
- [ ] **Optimizar carga** de datos

---

## 📋 Checklist de Implementación

### Pre-Implementación
- [ ] Crear branch: `refactor/security-and-quality-improvements`
- [ ] Backup del código actual
- [ ] Ejecutar tests existentes (baseline)
- [ ] Documentar estado actual

### Durante Implementación
- [ ] Implementar cambios incrementales
- [ ] Ejecutar tests después de cada cambio
- [ ] Commits frecuentes con mensajes descriptivos
- [ ] Revisar código con linters (pylint, flake8, mypy)

### Post-Implementación
- [ ] Ejecutar suite completa de tests
- [ ] Verificar que no hay regresiones
- [ ] Actualizar documentación
- [ ] Code review (si aplica)
- [ ] Merge a main/master

---

## 🎯 Priorización por Impacto/Esfuerzo

### Quick Wins (Alto Impacto, Bajo Esfuerzo)
1. ✅ Verificar `.gitignore` (ya hecho)
2. Reemplazar `print()` por logging (3-4h, 257 instancias)
3. Agregar type hints (2-3h, mejora legibilidad)
4. Implementar validación Pydantic (2-3h, previene ataques)

### Alto Impacto, Medio Esfuerzo
1. Autenticación/Autorización API (6-8h, crítico para seguridad)
2. Refactorizar funciones largas (4-6h, mejora mantenibilidad)
3. Tests de seguridad (6h, detecta vulnerabilidades)

### Medio Impacto, Alto Esfuerzo
1. Refactorizar arquitectura API (8h, mejora escalabilidad)
2. Optimizar performance (4-6h, mejora UX)

---

## 📊 Métricas de Éxito

### Seguridad
- [ ] 0 vulnerabilidades críticas
- [ ] 100% de endpoints protegidos
- [ ] 100% de inputs validados
- [ ] Rate limiting implementado

### Calidad de Código
- [ ] 0 instancias de `print()`
- [ ] Funciones < 40 líneas
- [ ] 100% de funciones con type hints
- [ ] Cobertura de tests > 80%

### Performance
- [ ] Tiempo de respuesta API < 200ms (p95)
- [ ] Caching implementado en endpoints críticos
- [ ] Sin memory leaks detectados

---

## 🔗 Referencias y Recursos

### Documentación
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Pydantic Validation](https://docs.pydantic.dev/latest/)
- [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html)
- [Supabase Auth](https://supabase.com/docs/guides/auth)

### Herramientas
- `bandit` - Análisis de seguridad estático
- `safety` - Verificación de vulnerabilidades en dependencias
- `mypy` - Type checking
- `pylint` / `flake8` - Linting
- `slowapi` - Rate limiting para FastAPI

---

## ⚠️ Notas Importantes

1. **No romper funcionalidad existente** - Todos los cambios deben mantener compatibilidad
2. **Tests primero** - Escribir tests antes de refactorizar cuando sea posible
3. **Commits pequeños** - Hacer commits frecuentes y descriptivos
4. **Code review** - Revisar cambios críticos antes de merge
5. **Documentación** - Actualizar README y docstrings con cambios

---

---

## 📝 TAREAS COMPLETADAS (2026-01-06)

### Backend y Deployment
- [x] **Backend desplegado y activo** en Render (`https://skypulsear-api.onrender.com`)
- [x] **API Keys configuradas** en Render (WINDY_POINT_FORECAST_API_KEY, METEOSOURCE_API_KEY)
- [x] **Fix router de health** - Endpoint `/api/v1/health/debug/repos` ahora accesible
- [x] **Importación condicional de WRFSMNRepository** - Evita error de boto3 si no está instalado

### Frontend
- [x] **Prioridad del backend** - Frontend intenta usar backend primero, luego Open-Meteo como fallback
- [x] **Manejo mejorado de errores 503** - Frontend detecta cuando backend no tiene fuentes configuradas
- [x] **Corrección de Windy API** - Cambio de GET a POST con JSON body (igual que backend)
- [x] **UX/UI mejorado** - Banner de advertencia y badge de estado para datos de ejemplo
- [x] **Cálculo de risk score corregido** - Incluye patternRisk, pesos corregidos

### Documentación
- [x] **Documentación de configuración** - Guías para configurar API keys en Render
- [x] **Documentación de diagnóstico** - Guías para diagnosticar problemas del backend

---

**Última actualización:** 2026-01-06  
**Próxima revisión:** Después de completar Fase 1
