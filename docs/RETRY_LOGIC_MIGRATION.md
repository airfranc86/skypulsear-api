# Migración de Retry Logic Manual a Decoradores Centralizados

## 📋 ¿Qué es la Migración de Retry Logic?

La **migración de retry logic** consiste en reemplazar el código de reintentos manual (escrito directamente en cada función) por decoradores reutilizables y centralizados.

## 🔄 Antes: Retry Logic Manual

**Problema:** Cada repositorio tenía su propia implementación de retry con código duplicado:

```python
def get_current_weather(self, latitude: float, longitude: float):
    max_retries = 3
    retry_delay = 1  # segundos
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return self._extract_data(response)
        except ConnectionError as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (2 ** attempt))  # Backoff exponencial
                continue
            else:
                return None
        except Timeout as e:
            return None
        # ... más manejo de errores
```

**Desventajas:**
- ❌ Código duplicado en cada método
- ❌ Difícil de mantener (cambios requieren modificar múltiples lugares)
- ❌ Inconsistencias entre implementaciones
- ❌ No hay jitter (riesgo de thundering herd)
- ❌ Logging inconsistente

## ✅ Después: Decoradores Centralizados

**Solución:** Usar decoradores reutilizables del módulo `app/utils/retry.py`:

```python
from app.utils.retry import retry_with_backoff

class WeatherRepository:
    @retry_with_backoff(
        max_attempts=3,
        initial_delay=1.0,
        multiplier=2.0,
        max_delay=10.0,
        jitter=True,
        retry_on=(ConnectionError, Timeout),
    )
    def get_current_weather(self, latitude: float, longitude: float):
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return self._extract_data(response)
```

**Ventajas:**
- ✅ Código DRY (Don't Repeat Yourself)
- ✅ Mantenimiento centralizado
- ✅ Consistencia garantizada
- ✅ Jitter automático para evitar thundering herd
- ✅ Logging estructurado automático
- ✅ Fácil de testear
- ✅ Configuración flexible por función

## 🎯 Funcionalidad del Decorador

### `@retry_with_backoff`

**Parámetros:**
- `max_attempts`: Número máximo de intentos (default: 3)
- `initial_delay`: Delay inicial en segundos (default: 1.0)
- `multiplier`: Multiplicador para exponential backoff (default: 2.0)
- `max_delay`: Delay máximo en segundos (default: 10.0)
- `jitter`: Si True, agrega variación aleatoria (default: True)
- `retry_on`: Tupla de excepciones que trigger retry (default: todas)

**Comportamiento:**
1. Intenta ejecutar la función
2. Si falla con una excepción en `retry_on`:
   - Calcula delay con exponential backoff: `delay = initial_delay * (multiplier ^ attempt)`
   - Agrega jitter si está habilitado: `delay = delay + (delay * 0.1 * random())`
   - Espera el delay calculado
   - Reintenta
3. Si todos los intentos fallan, re-lanza la última excepción
4. Registra logs estructurados automáticamente

**Ejemplo de delays:**
- Intento 1: falla → espera 1.0s
- Intento 2: falla → espera 2.0s (con jitter: ~2.0-2.2s)
- Intento 3: falla → espera 4.0s (con jitter: ~4.0-4.4s)
- Intento 4: falla → lanza excepción

### `@retry_async_with_backoff`

Versión asíncrona que usa `asyncio.sleep` en lugar de `time.sleep`.

## 🔧 Integración con Circuit Breakers

Los decoradores de retry funcionan **dentro** del circuit breaker:

```python
def get_current_weather(self, latitude: float, longitude: float):
    @retry_with_backoff(max_attempts=3, retry_on=(ConnectionError, Timeout))
    def _fetch_with_retry():
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return self._extract_data(response)
    
    # Circuit breaker protege la función con retry
    try:
        return self.circuit_breaker.call(_fetch_with_retry)
    except CircuitBreakerOpenError:
        return None
```

**Flujo:**
1. Circuit breaker verifica estado (CLOSED/OPEN/HALF_OPEN)
2. Si está CLOSED o HALF_OPEN, ejecuta la función
3. La función usa retry logic para manejar errores transitorios
4. Si falla repetidamente, el circuit breaker cuenta el fallo
5. Después de N fallos, el circuit breaker se abre (OPEN)
6. Requests futuros se rechazan inmediatamente hasta recovery timeout

## 📊 Beneficios de la Migración

### 1. **Mantenibilidad**
- Un solo lugar para actualizar la lógica de retry
- Cambios se propagan automáticamente a todos los usos

### 2. **Consistencia**
- Todos los repositorios usan la misma estrategia de retry
- Comportamiento predecible en toda la aplicación

### 3. **Observabilidad**
- Logs estructurados automáticos con contexto completo
- Fácil de monitorear y debuggear

### 4. **Testabilidad**
- Decoradores son funciones puras, fáciles de testear
- Mocking simplificado

### 5. **Performance**
- Jitter evita thundering herd problem
- Exponential backoff reduce carga en servicios externos

## 🚀 Pasos de Migración

1. **Identificar código de retry manual**
   - Buscar loops `for attempt in range(max_retries)`
   - Buscar `time.sleep()` con delays calculados

2. **Extraer función interna**
   - Crear función `_fetch_with_retry()` con la lógica de fetch
   - Aplicar decorador `@retry_with_backoff`

3. **Simplificar manejo de errores**
   - Remover loops manuales
   - Dejar que el decorador maneje los reintentos

4. **Integrar con circuit breaker**
   - Envolver la función con retry en `circuit_breaker.call()`

5. **Actualizar tests**
   - Verificar que los tests siguen funcionando
   - Agregar tests para el decorador si es necesario

## 📝 Ejemplo Completo

### Antes:
```python
def get_current_weather(self, lat: float, lon: float):
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params={...}, timeout=self.timeout)
            response.raise_for_status()
            return self._extract_data(response)
        except ConnectionError as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (2 ** attempt))
                continue
            return None
        except Timeout as e:
            return None
    return None
```

### Después:
```python
def get_current_weather(self, lat: float, lon: float):
    @retry_with_backoff(
        max_attempts=3,
        initial_delay=1.0,
        multiplier=2.0,
        retry_on=(ConnectionError, Timeout),
    )
    def _fetch_with_retry():
        response = requests.get(url, params={...}, timeout=self.timeout)
        response.raise_for_status()
        return self._extract_data(response)
    
    try:
        return self.circuit_breaker.call(_fetch_with_retry)
    except CircuitBreakerOpenError:
        logger.warning("Circuit breaker abierto para Windy")
        return None
```

## 🎓 Conceptos Clave

- **Exponential Backoff**: Delay aumenta exponencialmente (1s, 2s, 4s, 8s...)
- **Jitter**: Variación aleatoria para evitar sincronización de requests
- **Thundering Herd**: Problema cuando muchos requests se sincronizan
- **Circuit Breaker**: Patrón para prevenir cascading failures
- **Retry Logic**: Estrategia para manejar errores transitorios

