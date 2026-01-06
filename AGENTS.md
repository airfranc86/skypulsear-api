# SkyPulse - Agent Development Guidelines

## Project Overview
SkyPulse is a weather alert system for Argentina with FastAPI backend and vanilla JavaScript frontend. The system provides personalized risk scoring (0-5) and alert levels (0-4) based on user profiles and weather conditions.

## Build, Lint, and Test Commands

### Backend Commands
```bash
# Install dependencies
pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Run development server
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Code formatting
black .

# Linting
flake8 .

# Type checking
mypy .

# Security analysis
bandit -r .
```

### Testing Commands
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term --cov-report=xml -v

# Run specific test file
pytest tests/test_file.py

# Run specific test function
pytest tests/test_file.py::test_function

# Run by marker
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m slow          # Slow running tests only

# Run with verbose output
pytest -v tests/test_file.py::test_function
```

### Frontend Commands
```bash
# Deploy to Vercel (from public/ directory)
cd public
vercel --prod --yes
```

## Code Style Guidelines

### Python Conventions
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Imports**: Standard library → third-party → local imports (absolute from app root)
- **Type Hints**: Comprehensive with Optional, Union, and generic types
- **Line Length**: 88 characters (Black default)
- **String Quotes**: Double quotes for docstrings, single for strings

### Import Pattern Example
```python
# Standard library imports first
import logging
from datetime import UTC, datetime
from enum import IntEnum
from typing import Optional

# Third-party imports
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Local imports (absolute from app root)
from app.data.schemas.normalized_weather import UnifiedForecast
from app.services.alert_service import AlertLevel
from app.utils.logging_config import get_logger
```

### JavaScript Conventions
- **Naming**: camelCase for variables/functions, PascalCase for classes
- **Files**: kebab-case for frontend assets
- **Classes**: Use class-based patterns for weather clients
- **Async/Await**: Prefer async/await for API calls

### Error Handling Patterns

#### Custom Exception Hierarchy
```python
class SkyPulseError(Exception):
    """Base exception for SkyPulse errors."""

class WeatherDataError(SkyPulseError):
    """Weather data related errors."""

class APIError(SkyPulseError):
    """External API communication errors."""
```

#### Structured Error Handling
```python
try:
    result = await api_call()
except APIError as e:
    logger.error(f"API error: {e}")
    raise HTTPException(status_code=503, detail="External service unavailable")
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

### API Design Patterns
- RESTful endpoints with proper HTTP methods
- Pydantic models for request/response validation
- Comprehensive error responses with proper status codes
- Dependency injection for services and utilities
- Use `/api/v1/` prefix for all endpoints

### Logging Guidelines
- Use structured JSON logging with correlation IDs
- Proper log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Context-aware logging with request metadata
- Import logger from `app.utils.logging_config import get_logger`

## Architecture Guidelines

### Backend Structure
```
app/
├── api/                    # FastAPI application
│   ├── main.py            # Application entry point
│   ├── routers/           # API endpoints
│   ├── middleware/        # Custom middleware
│   └── dependencies.py    # FastAPI dependencies
├── data/                  # Data layer
│   ├── repositories/      # Data sources (Open-Meteo, Windy, WRF-SMN)
│   ├── processors/        # Data normalization and fusion
│   └── schemas/           # Pydantic models
├── services/              # Business logic
│   ├── risk_scoring.py    # 0-5 risk scoring by profile
│   ├── alert_service.py   # 0-4 alert levels
│   └── pattern_detector.py
└── utils/                 # Utilities (logging, exceptions, metrics)
```

### Frontend Structure
```
public/
├── dashboard.html         # Main dashboard
├── aviacion-demo.html     # Aviation-specific panel
├── js/                    # JavaScript utilities
├── open-meteo-client.js   # Primary weather client
├── alert-engine.js        # Frontend alert evaluation
└── alert-rules.json       # Declarative alert rules
```

## Key Architectural Decisions

1. **Frontend-First Mode**: System can operate completely without backend using Open-Meteo API
2. **Multi-Source Data**: Fusion of multiple weather APIs with confidence scoring
3. **Profile-Based Risk**: Personalized risk scoring (0-5) for different user types
4. **Alert Levels**: Separate alert system (0-4) aligned with SMN standards
5. **WRF-SMN Integration**: High-resolution weather data from AWS S3
6. **Circuit Breaker Pattern**: Protection against external API failures
7. **Comprehensive Logging**: Structured logging with correlation tracking

## Testing Guidelines

### Test Structure
- Use pytest with asyncio support
- Place tests in `tests/` directory
- Use markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Comprehensive test coverage with HTML, terminal, and XML reports

### Test Patterns
```python
import pytest
from app.data.schemas.normalized_weather import UnifiedForecast

@pytest.mark.unit
async def test_weather_data_processing():
    # Test implementation
    pass

@pytest.mark.integration
@pytest.mark.slow
async def test_external_api_integration():
    # Test implementation
    pass
```

## Development Workflow

1. **Before Committing**: Run `black .`, `flake8 .`, `mypy .`, and `pytest`
2. **Feature Development**: Create feature branches from main
3. **Code Review**: Ensure all tests pass and code quality checks are green
4. **Deployment**: Backend to Render, frontend to Vercel

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.12+)
- **Data Processing**: pandas, numpy, xarray, netCDF4
- **APIs**: Open-Meteo (primary), Windy (fallback), Meteosource (optional)
- **Validation**: Pydantic v2
- **Testing**: pytest with coverage
- **Code Quality**: Black, Flake8, MyPy, Bandit

### Frontend
- **Framework**: Vanilla JavaScript + HTML5
- **Visualization**: Chart.js, Plotly
- **Animations**: anime.js
- **Deployment**: Vercel

## Security Considerations
- Never commit secrets or API keys
- Use environment variables for configuration
- Implement proper CORS and security headers
- Regular security scans with Bandit
- Validate all inputs with Pydantic models