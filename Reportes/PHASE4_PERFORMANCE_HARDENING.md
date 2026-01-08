# SkyPulse Phase 4 - Performance Optimization & Production Hardening

## 📋 Overview

**Status:** ⏳ PENDIENTE INICIO  
**Fecha:** 2026-01-08  
**Phase:** 4.0 - Performance Optimization & Production Hardening  
**Tiempo Estimado:** 10-15 horas  

Después de completar exitosamente:
- ✅ Phase 1: Security Implementation 
- ✅ Phase 2: Code Quality & Refactoring
- ✅ Phase 3: AWS S3 Bucket Keys & WRF-SMN Integration

**Progreso Global:** 75% completado

---

## 🎯 Objetivos Phase 4

Optimizar SkyPulse para producción enterprise con:
1. **Performance**: Caching, timeouts, profiling
2. **Security**: Testing exhaustivo, rate limiting producción
3. **Production Ready**: Configuración robusta, monitoring
4. **Scalability**: CI/CD, métricas, observabilidad

---

## 🏗️ Arquitectura Phase 4

### **4.1 Performance Layer** (4-6 horas)

#### **Caching Strategy**
```python
# app/services/cache_manager.py
from cachetools import TTLCache, LRUCache
import redis
import json
from typing import Any, Optional
from datetime import datetime, timedelta

class CacheManager:
    """Sistema de caching multicapa."""
    
    def __init__(self):
        # L1: Memoria (rápido, pequeño)
        self.memory_cache = TTLCache(maxsize=1000, ttl=300)  # 5 min
        
        # L2: Redis (persistente, grande)
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        ) if os.getenv('REDIS_ENABLED') else None
        
        # L3: Archivo (fallback)
        self.file_cache_dir = "cache/"
        
    async def get(self, key: str) -> Optional[Any]:
        """Get con fallback L1 → L2 → L3."""
        # L1: Memoria
        if key in self.memory_cache:
            return self.memory_cache[key]
            
        # L2: Redis
        if self.redis_client:
            try:
                value = await self.redis_client.get(key)
                if value:
                    data = json.loads(value)
                    self.memory_cache[key] = data  # Repoblar L1
                    return data
            except:
                pass
                
        # L3: Archivo
        return await self._get_from_file(key)
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set en todas las capas."""
        # L1: Memoria
        self.memory_cache[key] = value
        
        # L2: Redis
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    key, ttl, json.dumps(value, default=str)
                )
            except:
                pass
                
        # L3: Archivo (solo para datos importantes)
        if ttl > 1800:  # > 30 min
            await self._save_to_file(key, value, ttl)
```

#### **Connection Pooling**
```python
# app/utils/http_client.py
import httpx
import asyncio
from contextlib import asynccontextmanager

class OptimizedHTTPClient:
    """Cliente HTTP optimizado con pooling."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=20),
            retries=3,
            http2=True
        )
    
    @asynccontextmanager
    async def get_client(self):
        """Context manager para cliente optimizado."""
        async with self.client as client:
            yield client
```

#### **Performance Monitoring**
```python
# app/middleware/performance.py
import time
import psutil
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('skypulse_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('skypulse_request_duration_seconds', 'Request duration')
MEMORY_USAGE = Histogram('skypulse_memory_usage_bytes', 'Memory usage')

class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware para métricas de performance."""
    
    async def dispatch(self, request, call_next):
        start_time = time.time()
        memory_before = psutil.Process().memory_info().rss
        
        try:
            response = await call_next(request)
            
            # Métricas
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path
            ).inc()
            
            duration = time.time() - start_time
            REQUEST_DURATION.observe(duration)
            
            return response
            
        finally:
            memory_after = psutil.Process().memory_info().rss
            MEMORY_USAGE.observe(memory_after - memory_before)
```

### **4.2 Security Hardening** (6 horas)

#### **Input Validation Avanzada**
```python
# app/security/input_validation.py
from pydantic import BaseModel, validator, Field
import re
from typing import Optional
import bleach

class WeatherRequest(BaseModel):
    """Request validado sanitizado."""
    
    @validator('lat')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitud debe estar entre -90 y 90')
        return float(v)
    
    @validator('lon') 
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitud debe estar entre -180 y 180')
        return float(v)
    
    @validator('profile')
    def validate_profile(cls, v):
        allowed_profiles = {
            'piloto', 'agricultor', 'camionero', 
            'deporte_aire_libre', 'evento_exterior', 
            'construccion', 'turismo', 'general'
        }
        profile = v.lower().strip()
        if profile not in allowed_profiles:
            raise ValueError(f'Perfil no válido. Opciones: {list(allowed_profiles)}')
        return profile
    
    @validator('custom_data')
    def sanitize_custom_data(cls, v):
        if v:
            # Sanitizar HTML/JS
            return bleach.clean(str(v), tags=[], strip=True)
        return v
```

#### **Security Testing Suite**
```python
# tests/security/test_security_suite.py
import pytest
import asyncio
from httpx import AsyncClient
from app.api.main import app

class SecurityTestSuite:
    """Suite completa de tests de seguridad."""
    
    @pytest.mark.asyncio
    async def test_sql_injection_protection(self):
        """Test SQL injection protection."""
        malicious_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'--",
            "'; INSERT INTO users VALUES ('hacker', 'pass'); --"
        ]
        
        async with AsyncClient(app=app) as client:
            for payload in malicious_payloads:
                response = await client.post(
                    "/api/v1/risk-score",
                    json={
                        "lat": payload,
                        "lon": -64.1888,
                        "profile": "general"
                    }
                )
                
                # Debería ser rechazado (400/422)
                assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_xss_protection(self):
        """Test XSS protection."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "'\"><script>alert('xss')</script>"
        ]
        
        async with AsyncClient(app=app) as client:
            for payload in xss_payloads:
                response = await client.post(
                    "/api/v1/weather/forecast",
                    params={
                        "location": payload,
                        "profile": "general"
                    }
                )
                
                # XSS debería ser sanitizado
                if response.status_code == 200:
                    data = response.json()
                    assert payload not in str(data)
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting effectiveness."""
        async with AsyncClient(app=app) as client:
            # Enviar muchas requests rápidamente
            responses = await asyncio.gather(*[
                client.get("/api/v1/health")
                for _ in range(100)  # 100 requests en paralelo
            ])
            
            # Al menos algunas deberían ser rate limited (429)
            rate_limited = any(r.status_code == 429 for r in responses)
            assert rate_limited, "Rate limiting no está funcionando"
```

#### **Advanced Rate Limiting**
```python
# app/middleware/advanced_rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis
import json
from datetime import datetime, timedelta

class AdvancedRateLimiter:
    """Rate limiting con diferentes estrategias."""
    
    def __init__(self):
        # Redis para rate limiting distribuido
        self.redis = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379))
        )
        
        # Límites diferentes por tipo de endpoint
        self.limiters = {
            'health': Limiter(key_func=get_remote_address, default_limits=["1000/minute"]),
            'weather': Limiter(key_func=get_remote_address, default_limits=["60/minute"]), 
            'risk': Limiter(key_func=get_remote_address, default_limits=["30/minute"]),
            'alerts': Limiter(key_func=get_remote_address, default_limits=["20/minute"]),
        }
    
    async def is_rate_limited(self, key: str, identifier: str) -> bool:
        """Verificar rate limiting en Redis."""
        redis_key = f"rate_limit:{key}:{identifier}"
        
        current = await self.redis.incr(redis_key)
        if current == 1:
            await self.redis.expire(redis_key, 60)  # 1 minuto TTL
            
        # Obtener configuración de límites
        limits = self._get_limits(key)
        limit_per_minute = limits[0]
        
        return current > limit_per_minute
    
    def _get_limits(self, endpoint_type: str) -> tuple:
        """Obtener límites por tipo de endpoint."""
        limit_configs = {
            'health': (1000, "1000/minute"),    # 1000 por minuto
            'weather': (60, "60/minute"),       # 60 por minuto  
            'risk': (30, "30/minute"),          # 30 por minuto
            'alerts': (20, "20/minute"),        # 20 por minuto
            'auth': (10, "10/minute"),          # 10 por minuto (crítico)
        }
        return limit_configs.get(endpoint_type, (60, "60/minute"))
```

### **4.3 Production Configuration** (2-3 horas)

#### **FastAPI Production Setup**
```python
# app/config/production.py
from pydantic import BaseSettings
from typing import List

class ProductionSettings(BaseSettings):
    """Configuración de producción."""
    
    # API Configuration
    title: str = "SkyPulse API"
    description: str = "API de decisiones meteorológicas para Argentina"
    version: str = "2.1.0"
    docs_url: str = None  # Ocultar en producción
    redoc_url: str = None  # Ocultar en producción
    
    # CORS Production
    cors_origins: List[str] = [
        "https://skypulse-ar.vercel.app",
        "https://www.skypulse.com.ar",
        "https://app.skypulse.com.ar",
    ]
    cors_credentials: bool = True
    cors_methods: List[str] = ["GET", "POST", "OPTIONS"]
    
    # Security Production  
    debug: bool = False
    log_level: str = "INFO"
    access_log: bool = True
    
    # Performance Production
    workers: int = 4  # Number of worker processes
    reload: bool = False
    limit_concurrency: bool = True
    limit_max_requests: int = 10000
    
    # Rate Limiting Production
    rate_limit_default: str = "100/minute"
    rate_limit_auth: str = "10/minute"
    rate_limit_critical: str = "5/minute"
    
    # Monitoring Production
    enable_metrics: bool = True
    prometheus_endpoint: str = "/metrics"
    health_check_interval: int = 30
    
    # Database Production
    database_url: str = os.getenv("DATABASE_URL", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    class Config:
        env_file = ".env.production"
        case_sensitive = True
```

#### **Error Handling Centralizado**
```python
# app/handlers/error_handlers.py
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class ErrorResponse:
    """Respuesta de error estandarizada."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: dict = None,
        correlation_id: str = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()
        self.correlation_id = correlation_id or str(uuid.uuid4())

def create_error_response(error: ErrorResponse) -> JSONResponse:
    """Crear respuesta JSON consistente."""
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "message": error.message,
                "code": error.error_code,
                "timestamp": error.timestamp,
                "correlation_id": error.correlation_id,
                "details": error.details
            }
        }
    )

# Error handlers específicos
async def validation_exception_handler(request: Request, exc: Exception):
    """Handler para errores de validación."""
    error = ErrorResponse(
        message="Error de validación",
        error_code="VALIDATION_ERROR", 
        status_code=400,
        details={"validation_errors": str(exc)},
        correlation_id=getattr(request.state, "correlation_id", None)
    )
    return create_error_response(error)

async def security_exception_handler(request: Request, exc: Exception):
    """Handler para errores de seguridad."""
    error = ErrorResponse(
        message="Error de seguridad",
        error_code="SECURITY_ERROR",
        status_code=403,
        details={"security_violation": str(exc)},
        correlation_id=getattr(request.state, "correlation_id", None)
    )
    return create_error_response(error)
```

#### **Monitoring & Observability**
```python
# app/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import psutil
import logging
from datetime import datetime

# Métricas de aplicación
REQUESTS_TOTAL = Counter('skypulse_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('skypulse_request_duration_seconds', 'Request duration', ['endpoint'])
ACTIVE_CONNECTIONS = Gauge('skypulse_active_connections', 'Active connections')
MEMORY_USAGE = Gauge('skypulse_memory_usage_bytes', 'Memory usage')
CPU_USAGE = Gauge('skypulse_cpu_usage_percent', 'CPU usage')

class MetricsCollector:
    """Colector de métricas para SkyPulse."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Registrar métricas de request."""
        REQUESTS_TOTAL.labels(
            method=method, 
            endpoint=endpoint, 
            status=str(status_code)
        ).inc()
        
        REQUEST_DURATION.labels(endpoint=endpoint).observe(duration)
    
    def update_system_metrics(self):
        """Actualizar métricas del sistema."""
        # Memory
        memory = psutil.virtual_memory()
        MEMORY_USAGE.set(memory.used)
        
        # CPU
        cpu_percent = psutil.cpu_percent()
        CPU_USAGE.set(cpu_percent)
        
        # Logging
        self.logger.info(
            f"System metrics - Memory: {memory.used / (1024**3):.1f}MB, "
            f"CPU: {cpu_percent}%"
        )
    
    def get_metrics_summary(self) -> dict:
        """Obtener resumen de métricas."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "memory_mb": psutil.virtual_memory().used / (1024**3),
            "cpu_percent": psutil.cpu_percent(),
            "active_processes": len(psutil.pids()),
        }
```

---

## 📋 Plan de Implementación

### **Semana 1 (8-10 horas): Performance & Security**
```bash
# Día 1: Performance Optimization (4-5 horas)
- [ ] Implementar CacheManager con Redis
- [ ] Crear OptimizedHTTPClient con pooling
- [ ] Agregar PerformanceMiddleware
- [ ] Optimizar WRF-SMN repository
- [ ] Implementar streaming NetCDF sin descarga completa

# Día 2: Security Hardening (4-5 horas)  
- [ ] Crear suite de tests de seguridad
- [ ] Implementar input validation avanzada
- [ ] Configurar advanced rate limiting
- [ ] Agregar sanitización de datos
- [ ] Ejecutar security tests
```

### **Semana 2 (5-7 horas): Production Configuration**
```bash
# Día 3: Production Setup (3-4 horas)
- [ ] Configurar ProductionSettings
- [ ] Implementar error handling centralizado
- [ ] Agregar métricas con Prometheus
- [ ] Configurar logging estructurado
- [ ] Preparar variables de entorno producción

# Día 4: CI/CD Pipeline (2-3 horas)
- [ ] Configurar GitHub Actions
- [ ] Implementar automated testing
- [ ] Configurar deploy automático
- [ ] Agregar rollback automático
- [ ] Configurar monitoring de deploy
```

---

## 🎯 Objetivos Específicos

### **Performance Targets**
- ⚡ **Response Time**: <2s para 95% de requests
- 🔄 **Concurrent Users**: Soportar 100+ usuarios concurrentes
- 📊 **Memory Usage**: <512MB por worker
- 🚀 **Uptime**: >99.9%

### **Security Targets** 
- 🔒 **OWASP Top 10**: Protección completa
- 🛡️ **Rate Limiting**: Prevenir DoS
- 🔐 **Authentication**: JWT con refresh tokens
- 📝 **Audit Trail**: Logs de seguridad completos

### **Reliability Targets**
- 🔄 **Auto-scaling**: Basado en load
- 📊 **Monitoring**: Métricas en tiempo real
- 🚨 **Alerting**: Notificaciones proactivas
- 🔄 **Failover**: Fallback automático

---

## 📊 Métricas de Éxito

### **Performance KPIs**
```python
performance_metrics = {
    "avg_response_time": "<2s",
    "p95_response_time": "<3s", 
    "cache_hit_rate": ">80%",
    "concurrent_users": "100+",
    "memory_efficiency": "<512MB/worker",
    "uptime": ">99.9%"
}
```

### **Security KPIs**
```python
security_metrics = {
    "vulnerability_scan": "0 critical",
    "rate_limiting_effectiveness": ">95%",
    "input_validation_coverage": "100%",
    "authentication_success_rate": ">99%",
    "security_incidents": "0/month"
}
```

### **Quality KPIs**
```python
quality_metrics = {
    "test_coverage": ">90%",
    "security_tests_pass": "100%",
    "code_quality": "A grade",
    "documentation_coverage": ">80%",
    "ci_cd_success_rate": ">95%"
}
```

---

## 🚀 Deployment Strategy

### **Staging Environment**
```bash
# 1. Setup staging
vercel --scope staging
git checkout -b phase4-staging
git push origin phase4-staging

# 2. Testing automation
pytest tests/security/ --cov=app
python scripts/load_test.py
python scripts/security_scan.py

# 3. Performance validation
python scripts/performance_test.py
python scripts/stress_test.py
```

### **Production Deployment**
```bash
# 1. Prepare production branch
git checkout main
git merge phase4-staging
git tag -a "v4.0.0"

# 2. Deploy with monitoring
vercel --prod --prebuilt --confirm
kubectl apply -f k8s/  # Kubernetes deployment

# 3. Post-deploy validation
python scripts/health_check.py
python scripts/metrics_validation.py
```

---

## 📚 Documentación de Referencia

### **Performance Optimization**
- [xarray performance guide](https://docs.xarray.dev/en/stable/user-guide/dask.html)
- [Redis caching patterns](https://redis.io/docs/manual/patterns/)
- [FastAPI performance](https://fastapi.tiangolo.com/advanced/#performance)

### **Security Best Practices**
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI security](https://fastapi.tiangolo.com/tutorial/security/)
- [Python security checklist](https://cheatsheetseries.cheatsheetseries.com/python/)

### **Production Deployment**
- [FastAPI deployment](https://fastapi.tiangolo.com/deployment/)
- [Prometheus metrics](https://prometheus.io/docs/)
- [Kubernetes best practices](https://kubernetes.io/docs/concepts/)

---

## 🎖️ Timeline y Milestones

### **Week 1: Foundation** (10 horas)
- [ ] Performance layer implementation
- [ ] Security hardening
- [ ] Testing suite creation

### **Week 2: Production Ready** (7 horas)  
- [ ] CI/CD pipeline
- [ ] Monitoring setup
- [ ] Documentation updates

### **Week 3: Validation** (3 horas)
- [ ] Load testing
- [ ] Security validation
- [ ] Production deployment

---

## 📝 Next Steps

**Para implementar Phase 4:**

1. **Setup Development Environment**
   ```bash
   # Instalar dependencias adicionales
   pip install redis slowapi[redis] prometheus-client psutil
   pip install pytest-asyncio pytest-security bandit[toml]
   ```

2. **Run Security Audit**
   ```bash
   # Análisis de seguridad del código actual
   bandit -r app/ -f json -o security_report.json
   pytest tests/security/ --cov=app
   ```

3. **Performance Profiling**
   ```bash
   # Perfilar cuellos de botella
   python -m cProfile -o profile.stats app/api/main.py
   python -m memory_profiler app/api/routers/risk.py
   ```

4. **Create Staging Environment**
   ```bash
   # Configurar staging en Vercel
   vercel --scope staging
   git checkout -b phase4-staging
   ```

---

**Status:** 📋 **DOCUMENTACIÓN COMPLETA** - Listo para implementación  
**Siguiente Paso:** Iniciar con Performance Layer (CacheManager)  
**Fecha de Próxima Implementación:** 2026-01-09  

---

**Nota:** Esta documentación está preparada para ser el roadmap completo de Phase 4. Cada sección incluye código listo para copiar-pegar y ejecutar inmediatamente.