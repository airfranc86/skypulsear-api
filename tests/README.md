# Tests de SkyPulse API

Tests para los endpoints de la API FastAPI de SkyPulse.

## Estructura

```
tests/
├── __init__.py
├── conftest.py              # Configuración compartida (fixtures)
├── test_health.py           # Tests del endpoint /health
├── test_weather_endpoints.py    # Tests de /api/v1/weather/*
├── test_risk_endpoints.py       # Tests de /api/v1/risk-score
├── test_alerts_endpoints.py    # Tests de /api/v1/alerts/*
├── test_patterns_endpoints.py  # Tests de /api/v1/patterns/*
└── test_api_integration.py     # Tests de integración end-to-end
```

## Ejecutar Tests

### Todos los tests

```bash
pytest
```

### Tests específicos

```bash
# Solo tests de health
pytest tests/test_health.py

# Solo tests de integración
pytest -m integration

# Tests lentos (requieren APIs reales)
pytest -m slow

# Con cobertura
pytest --cov=app --cov-report=html
```

### Opciones útiles

```bash
# Verbose (ver más detalles)
pytest -v

# Ver prints/logs
pytest -s

# Parar en primer error
pytest -x

# Ejecutar solo tests que fallaron anteriormente
pytest --lf
```

## Marcadores

- `@pytest.mark.integration`: Tests de integración (pueden requerir APIs externas)
- `@pytest.mark.slow`: Tests lentos (requieren APIs reales)

## Notas

- Los tests de integración pueden fallar si las APIs externas (Meteosource, Windy) no están disponibles
- Los tests están diseñados para manejar errores 503 (servicio no disponible) gracefully
- Los tests de validación (coordenadas inválidas, perfiles inválidos) siempre deberían pasar

## Cobertura

Para ver el reporte de cobertura:

```bash
pytest --cov=app --cov-report=html
```

Luego abrir `htmlcov/index.html` en el navegador.

