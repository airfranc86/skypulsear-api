"""Tests unitarios del motor de clasificación de amenazas (M2.2)."""

import pytest

from app.models.threat_classification import ThreatType
from app.services.threat_classification import ThreatClassificationInput, classify_threats


def test_classify_threats_empty_input_returns_empty_list() -> None:
    """Sin datos relevantes no se clasifica amenaza."""
    data = ThreatClassificationInput(
        temperature_celsius=20.0,
        precipitation_mm=0.0,
        cloud_cover_pct=30.0,
    )
    result = classify_threats(data)
    assert result == []


def test_classify_threats_hail_proxy_with_radar() -> None:
    """Con dBZ y nivel 0°C se clasifica proxy granizo."""
    data = ThreatClassificationInput(
        temperature_celsius=5.0,
        precipitation_mm=2.0,
        reflectivity_dbz=55.0,
        freezing_level_m=2000.0,
    )
    result = classify_threats(data)
    assert len(result) == 1
    assert result[0].threat_type == ThreatType.HAIL_PROXY
    assert result[0].level >= 2
    assert "dBZ" in result[0].criterion_used


def test_classify_threats_hail_proxy_without_radar_cold_heavy_precip() -> None:
    """Precipitación fuerte y temperatura baja → proxy granizo (sin radar)."""
    data = ThreatClassificationInput(
        temperature_celsius=2.0,
        precipitation_mm=10.0,
        cloud_cover_pct=80.0,
    )
    result = classify_threats(data)
    assert len(result) == 1
    assert result[0].threat_type == ThreatType.HAIL_PROXY
    assert "precip" in result[0].criterion_used.lower() or "T=" in result[0].criterion_used


def test_classify_threats_severe_convection() -> None:
    """Precipitación y nubosidad altas → convección severa."""
    data = ThreatClassificationInput(
        temperature_celsius=25.0,
        precipitation_mm=9.0,
        cloud_cover_pct=75.0,
    )
    result = classify_threats(data)
    assert len(result) == 1
    assert result[0].threat_type == ThreatType.SEVERE_CONVECTION
    assert result[0].level >= 1


def test_classify_threats_weather_code_thunderstorm() -> None:
    """Código WMO de tormenta (95, 96, 99) → convección severa."""
    data = ThreatClassificationInput(
        temperature_celsius=22.0,
        precipitation_mm=1.0,
        cloud_cover_pct=50.0,
        weather_code=96,
    )
    result = classify_threats(data)
    assert len(result) == 1
    assert result[0].threat_type == ThreatType.SEVERE_CONVECTION
    assert "weather_code" in result[0].criterion_used
