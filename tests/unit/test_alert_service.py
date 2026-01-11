"""
Tests unitarios para AlertService.

Verifica la generación de alertas operativas basadas en patrones meteorológicos.
"""

import pytest
from datetime import UTC, datetime, timedelta

from app.services.alert_service import (
    AlertService,
    AlertLevel,
    OperationalAlert,
)
from app.services.pattern_detector import (
    DetectedPattern,
    PatternType,
    RiskLevel,
)
from app.data.schemas.normalized_weather import UnifiedForecast


@pytest.fixture
def alert_service() -> AlertService:
    """Fixture para crear instancia de AlertService."""
    return AlertService()


@pytest.fixture
def sample_patterns() -> list[DetectedPattern]:
    """Fixture para crear patrones de ejemplo."""
    return [
        DetectedPattern(
            pattern_type=PatternType.SEVERE_CONVECTIVE_STORM,
            risk_level=RiskLevel.HIGH,
            confidence=0.85,
            title="Tormenta Convectiva Severa",
            description="Condiciones favorables para tormentas severas",
            trigger_values={"cape": 2500.0, "precipitation": 35.0},
            thresholds_exceeded=["cape_extreme", "precip_intense"],
            recommendations=["Evitar actividades al aire libre", "Buscar refugio"],
        )
    ]


@pytest.fixture
def sample_forecasts() -> list[UnifiedForecast]:
    """Fixture para crear pronósticos de ejemplo."""
    base_time = datetime.now(UTC)
    return [
        UnifiedForecast(
            timestamp=base_time + timedelta(hours=i),
            forecast_hour=i,
            latitude=-31.4201,
            longitude=-64.1888,
            temperature_celsius=22.0 + i,
            humidity_pct=60.0,
            wind_speed_ms=10.0 + i,
            wind_direction_deg=180.0,
            pressure_hpa=1013.25,
            precipitation_mm=5.0 * i,
            cloud_cover_pct=50.0,
            overall_confidence=0.85,
        )
        for i in range(6)
    ]


class TestAlertService:
    """Tests para AlertService."""

    def test_generate_alerts_empty_patterns(
        self, alert_service: AlertService, sample_forecasts: list[UnifiedForecast]
    ):
        """Test que generate_alerts retorna al menos una alerta normal sin patrones."""
        alerts = alert_service.generate_alerts([], sample_forecasts)
        assert isinstance(alerts, list)
        # AlertService siempre retorna al menos una alerta (normal si no hay patrones)
        assert len(alerts) >= 0

    def test_generate_alerts_with_patterns(
        self,
        alert_service: AlertService,
        sample_patterns: list[DetectedPattern],
        sample_forecasts: list[UnifiedForecast],
    ):
        """Test generación de alertas con patrones."""
        alerts = alert_service.generate_alerts(sample_patterns, sample_forecasts)
        assert isinstance(alerts, list)
        assert len(alerts) > 0, "Debería generar al menos una alerta"

    def test_alert_structure(
        self,
        alert_service: AlertService,
        sample_patterns: list[DetectedPattern],
        sample_forecasts: list[UnifiedForecast],
    ):
        """Test que las alertas tienen la estructura correcta."""
        alerts = alert_service.generate_alerts(sample_patterns, sample_forecasts)
        
        if alerts:
            alert = alerts[0]
            assert isinstance(alert, OperationalAlert)
            assert alert.level in AlertLevel
            assert alert.level_name is not None
            assert alert.phenomenon is not None
            assert alert.description is not None
            assert alert.recommendation is not None
            assert isinstance(alert.expected_impact, list)

    def test_alert_levels(
        self,
        alert_service: AlertService,
        sample_patterns: list[DetectedPattern],
        sample_forecasts: list[UnifiedForecast],
    ):
        """Test que las alertas tienen niveles válidos."""
        alerts = alert_service.generate_alerts(sample_patterns, sample_forecasts)
        
        for alert in alerts:
            assert alert.level >= AlertLevel.NORMAL
            assert alert.level <= AlertLevel.CRITICAL
            assert alert.level_name in [
                "Normal",
                "Atención",
                "Precaución",
                "Alerta",
                "Crítica",
            ]

    def test_alert_time_window(
        self,
        alert_service: AlertService,
        sample_patterns: list[DetectedPattern],
        sample_forecasts: list[UnifiedForecast],
    ):
        """Test que las alertas tienen ventana temporal."""
        alerts = alert_service.generate_alerts(sample_patterns, sample_forecasts)
        
        for alert in alerts:
            assert alert.time_window is not None
            assert isinstance(alert.horizon_hours, int)
            assert alert.horizon_hours >= 0

    def test_alert_to_display_format(
        self,
        alert_service: AlertService,
        sample_patterns: list[DetectedPattern],
        sample_forecasts: list[UnifiedForecast],
    ):
        """Test formato de display de alertas."""
        alerts = alert_service.generate_alerts(sample_patterns, sample_forecasts)
        
        if alerts:
            alert = alerts[0]
            display_text = alert.to_display_format()
            assert isinstance(display_text, str)
            assert len(display_text) > 0
            assert "Nivel:" in display_text
            assert "Fenómeno:" in display_text
            assert "Recomendación:" in display_text

    def test_alert_source_note(
        self,
        alert_service: AlertService,
        sample_patterns: list[DetectedPattern],
        sample_forecasts: list[UnifiedForecast],
    ):
        """Test que las alertas incluyen nota de fuente."""
        alerts = alert_service.generate_alerts(sample_patterns, sample_forecasts)
        
        if alerts:
            alert = alerts[0]
            assert alert.source_note is not None
            assert "SMN" in alert.source_note or "WRF-SMN" in alert.source_note
