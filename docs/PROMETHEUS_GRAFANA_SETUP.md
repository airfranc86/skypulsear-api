# Configuración de Prometheus y Grafana para SkyPulse

## 📊 Descripción

Este documento explica cómo configurar Prometheus y Grafana para monitorear las métricas de SkyPulse API.

## 🚀 Inicio Rápido

### 1. Iniciar Stack de Monitoreo

```bash
# Iniciar Prometheus y Grafana
docker-compose -f docker-compose.monitoring.yml up -d

# Verificar que los servicios estén corriendo
docker-compose -f docker-compose.monitoring.yml ps
```

### 2. Acceder a las Interfaces

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001
  - Usuario: `admin`
  - Contraseña: `admin` (cambiar en producción)

### 3. Verificar Métricas

En Prometheus, ejecutar queries de prueba:
```promql
# Total de requests HTTP
http_requests_total

# Latencia p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Estado de circuit breakers
circuit_breaker_state

# Fallos de circuit breakers
circuit_breaker_failures_total
```

## 📁 Estructura de Archivos

```
SkyPulse/
├── prometheus.yml                    # Configuración de Prometheus
├── docker-compose.monitoring.yml     # Stack de monitoreo
└── grafana/
    ├── provisioning/
    │   ├── datasources/
    │   │   └── prometheus.yml        # Datasource automático
    │   └── dashboards/
    │       └── default.yml           # Configuración de dashboards
    └── dashboards/
        └── skypulse-overview.json    # Dashboard principal
```

## 🔧 Configuración Detallada

### Prometheus

El archivo `prometheus.yml` configura:
- **Scrape interval**: 15 segundos
- **Target**: SkyPulse API en `http://host.docker.internal:8000/metrics`
- **Retention**: 200 horas de datos

**Para producción en Render:**
```yaml
scrape_configs:
  - job_name: 'skypulse-api'
    static_configs:
      - targets: ['skypulse-api.onrender.com']
        scheme: 'https'
```

### Grafana

**Datasource**: Configurado automáticamente para conectarse a Prometheus.

**Dashboards**: 
- `skypulse-overview.json`: Dashboard principal con métricas clave

## 📈 Métricas Disponibles

### HTTP Metrics
- `http_requests_total`: Total de requests HTTP
- `http_request_duration_seconds`: Latencia de requests
- `http_request_errors_total`: Total de errores HTTP

### Circuit Breaker Metrics
- `circuit_breaker_state`: Estado actual (0=closed, 1=open, 2=half_open)
- `circuit_breaker_failures_total`: Total de fallos

### Weather Source Metrics
- `weather_source_availability`: Disponibilidad de fuentes (1=disponible, 0=no disponible)
- `weather_source_request_duration_seconds`: Latencia de requests a fuentes

### Cache Metrics
- `cache_hits_total`: Total de cache hits
- `cache_misses_total`: Total de cache misses

## 🎨 Queries PromQL Útiles

### Request Rate por Endpoint
```promql
rate(http_requests_total[5m])
```

### Latencia p95 por Endpoint
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Error Rate
```promql
rate(http_request_errors_total[5m])
```

### Circuit Breaker Abierto
```promql
circuit_breaker_state == 1
```

### Disponibilidad de Fuentes
```promql
weather_source_availability
```

## 🚨 Alertas Recomendadas

### Circuit Breaker Abierto
```yaml
- alert: CircuitBreakerOpen
  expr: circuit_breaker_state == 1
  for: 5m
  annotations:
    summary: "Circuit breaker {{ $labels.circuit_name }} está abierto"
```

### Alta Latencia
```yaml
- alert: HighLatency
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
  for: 5m
  annotations:
    summary: "Latencia p95 > 2s en {{ $labels.endpoint }}"
```

### Alta Tasa de Errores
```yaml
- alert: HighErrorRate
  expr: rate(http_request_errors_total[5m]) > 0.1
  for: 5m
  annotations:
    summary: "Tasa de errores > 10% en {{ $labels.endpoint }}"
```

## 🔄 Actualizar Configuración

### Prometheus
```bash
# Recargar configuración sin reiniciar
curl -X POST http://localhost:9090/-/reload
```

### Grafana
- Cambios en dashboards se reflejan automáticamente
- Para cambios en datasources, editar `grafana/provisioning/datasources/prometheus.yml`

## 🐳 Producción

### Variables de Entorno
```bash
# Cambiar credenciales de Grafana
GF_SECURITY_ADMIN_PASSWORD=tu_password_seguro
```

### Volúmenes Persistentes
Los datos se persisten en volúmenes Docker:
- `prometheus_data`: Datos históricos de Prometheus
- `grafana_data`: Configuración y dashboards de Grafana

### Backup
```bash
# Backup de Prometheus
docker run --rm -v skypulse_prometheus_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/prometheus-backup.tar.gz /data

# Backup de Grafana
docker run --rm -v skypulse_grafana_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/grafana-backup.tar.gz /data
```

## 📚 Recursos

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Tutorial](https://prometheus.io/docs/prometheus/latest/querying/basics/)

