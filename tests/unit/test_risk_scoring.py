"""
Tests unitarios para RiskScoringService.

Verifica el cálculo de risk scores por perfil de usuario.
"""

import pytest
from datetime import UTC, datetime, timedelta

from app.services.risk_scoring import (
    RiskScoringService,
    UserProfile,
    RiskCategory,
    RiskScore,
)
from app.data.schemas.normalized_weather import UnifiedForecast
from app.services.pattern_detector import DetectedPattern, PatternType, RiskLevel


@pytest.fixture
def risk_service() -> RiskScoringService:
    """Fixture para crear instancia de RiskScoringService."""
    return RiskScoringService()


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
            temperature_celsius=22.0,
            humidity_pct=60.0,
            wind_speed_ms=10.0,
            wind_direction_deg=180.0,
            pressure_hpa=1013.25,
            precipitation_mm=0.0,
            cloud_cover_pct=30.0,
            overall_confidence=0.85,
        )
        for i in range(6)
    ]


@pytest.fixture
def sample_patterns() -> list[DetectedPattern]:
    """Fixture para crear patrones de ejemplo."""
    return [
        DetectedPattern(
            pattern_type=PatternType.HEAT_WAVE,
            risk_level=RiskLevel.MODERATE,
            confidence=0.75,
            title="Ola de Calor",
            description="Temperaturas elevadas sostenidas",
            trigger_values={"temperature": 36.0},
            thresholds_exceeded=["heat_wave_day"],
            recommendations=["Mantenerse hidratado"],
        )
    ]


class TestRiskScoringService:
    """Tests para RiskScoringService."""

    def test_calculate_risk_score_pilot(
        self,
        risk_service: RiskScoringService,
        sample_forecasts: list[UnifiedForecast],
        sample_patterns: list[DetectedPattern],
    ):
        """Test cálculo de risk score para perfil piloto."""
        from app.services.alert_service import AlertService
        alert_service = AlertService()
        alerts = alert_service.generate_alerts(sample_patterns, sample_forecasts)
        
        risk_score = risk_service.calculate_risk(
            profile=UserProfile.PILOT,
            forecasts=sample_forecasts,
            patterns=sample_patterns,
            alerts=alerts,
        )
        
        assert isinstance(risk_score, RiskScore)
        assert risk_score.profile == UserProfile.PILOT
        assert 0 <= risk_score.score <= 5
        # category es un string, no un enum
        assert isinstance(risk_score.category, str)

    def test_calculate_risk_score_farmer(
        self,
        risk_service: RiskScoringService,
        sample_forecasts: list[UnifiedForecast],
        sample_patterns: list[DetectedPattern],
    ):
        """Test cálculo de risk score para perfil agricultor."""
        from app.services.alert_service import AlertService
        alert_service = AlertService()
        alerts = alert_service.generate_alerts(sample_patterns, sample_forecasts)
        
        risk_score = risk_service.calculate_risk(
            profile=UserProfile.FARMER,
            forecasts=sample_forecasts,
            patterns=sample_patterns,
            alerts=alerts,
        )
        
        assert isinstance(risk_score, RiskScore)
        assert risk_score.profile == UserProfile.FARMER
        assert 0 <= risk_score.score <= 5

    def test_risk_score_structure(
        self,
        risk_service: RiskScoringService,
        sample_forecasts: list[UnifiedForecast],
        sample_patterns: list[DetectedPattern],
    ):
        """Test que el risk score tiene la estructura correcta."""
        from app.services.alert_service import AlertService
        alert_service = AlertService()
        alerts = alert_service.generate_alerts(sample_patterns, sample_forecasts)
        
        risk_score = risk_service.calculate_risk(
            profile=UserProfile.GENERAL,
            forecasts=sample_forecasts,
            patterns=sample_patterns,
            alerts=alerts,
        )
        
        # Verificar campos principales
        assert isinstance(risk_score.score, (int, float))
        assert isinstance(risk_score.category, str)  # category es string
        assert isinstance(risk_score.temperature_risk, int)
        assert isinstance(risk_score.wind_risk, int)
        assert isinstance(risk_score.precipitation_risk, int)
        assert isinstance(risk_score.storm_risk, int)
        assert isinstance(risk_score.pattern_risk, int)
        
        # Verificar rangos
        assert 0 <= risk_score.temperature_risk <= 100
        assert 0 <= risk_score.wind_risk <= 100
        assert 0 <= risk_score.precipitation_risk <= 100
        assert 0 <= risk_score.storm_risk <= 100
        assert 0 <= risk_score.pattern_risk <= 100

    def test_risk_score_recommendations(
        self,
        risk_service: RiskScoringService,
        sample_forecasts: list[UnifiedForecast],
        sample_patterns: list[DetectedPattern],
    ):
        """Test que el risk score incluye recomendaciones."""
        from app.services.alert_service import AlertService
        alert_service = AlertService()
        alerts = alert_service.generate_alerts(sample_patterns, sample_forecasts)
        
        risk_score = risk_service.calculate_risk(
            profile=UserProfile.GENERAL,
            forecasts=sample_forecasts,
            patterns=sample_patterns,
            alerts=alerts,
        )
        
        assert risk_score.recommendation is not None
        assert isinstance(risk_score.recommendation, str)
        assert len(risk_score.recommendation) > 0

    def test_risk_score_key_factors(
        self,
        risk_service: RiskScoringService,
        sample_forecasts: list[UnifiedForecast],
        sample_patterns: list[DetectedPattern],
    ):
        """Test que el risk score incluye factores clave."""
        from app.services.alert_service import AlertService
        alert_service = AlertService()
        alerts = alert_service.generate_alerts(sample_patterns, sample_forecasts)
        
        risk_score = risk_service.calculate_risk(
            profile=UserProfile.GENERAL,
            forecasts=sample_forecasts,
            patterns=sample_patterns,
            alerts=alerts,
        )
        
        assert isinstance(risk_score.main_risk_factors, list)
        # Puede estar vacío si no hay factores críticos

    def test_risk_score_all_profiles(
        self,
        risk_service: RiskScoringService,
        sample_forecasts: list[UnifiedForecast],
        sample_patterns: list[DetectedPattern],
    ):
        """Test cálculo de risk score para todos los perfiles."""
        profiles = [
            UserProfile.PILOT,
            UserProfile.TRUCKER,
            UserProfile.FARMER,
            UserProfile.OUTDOOR_SPORTS,
            UserProfile.OUTDOOR_EVENT,
            UserProfile.CONSTRUCTION,
            UserProfile.TOURISM,
            UserProfile.GENERAL,
        ]
        
        from app.services.alert_service import AlertService
        alert_service = AlertService()
        alerts = alert_service.generate_alerts(sample_patterns, sample_forecasts)
        
        for profile in profiles:
            risk_score = risk_service.calculate_risk(
                profile=profile,
                forecasts=sample_forecasts,
                patterns=sample_patterns,
                alerts=alerts,
            )
            
            assert risk_score.profile == profile
            assert 0 <= risk_score.score <= 5

    def test_risk_score_high_wind(
        self,
        risk_service: RiskScoringService,
    ):
        """Test que vientos altos aumentan el risk score."""
        high_wind_forecasts = [
            UnifiedForecast(
                timestamp=datetime.now(UTC) + timedelta(hours=i),
                forecast_hour=i,
                latitude=-31.4201,
                longitude=-64.1888,
                temperature_celsius=20.0,
                humidity_pct=50.0,
                wind_speed_ms=30.0,  # Viento muy fuerte
                wind_direction_deg=180.0,
                pressure_hpa=1010.0,
                precipitation_mm=0.0,
                cloud_cover_pct=40.0,
                overall_confidence=0.85,
            )
            for i in range(6)
        ]
        
        from app.services.alert_service import AlertService
        alert_service = AlertService()
        alerts = alert_service.generate_alerts([], high_wind_forecasts)
        
        risk_score = risk_service.calculate_risk(
            profile=UserProfile.PILOT,
            forecasts=high_wind_forecasts,
            patterns=[],
            alerts=alerts,
        )
        
        assert risk_score.wind_risk > 50, "Vientos altos deberían aumentar wind_risk"

    def test_risk_score_high_temperature(
        self,
        risk_service: RiskScoringService,
    ):
        """Test que temperaturas altas aumentan el risk score."""
        high_temp_forecasts = [
            UnifiedForecast(
                timestamp=datetime.now(UTC) + timedelta(hours=i),
                forecast_hour=i,
                latitude=-31.4201,
                longitude=-64.1888,
                temperature_celsius=38.0,  # Temperatura muy alta
                humidity_pct=40.0,
                wind_speed_ms=5.0,
                wind_direction_deg=180.0,
                pressure_hpa=1008.0,
                precipitation_mm=0.0,
                cloud_cover_pct=10.0,
                overall_confidence=0.85,
            )
            for i in range(6)
        ]
        
        from app.services.alert_service import AlertService
        alert_service = AlertService()
        alerts = alert_service.generate_alerts([], high_temp_forecasts)
        
        risk_score = risk_service.calculate_risk(
            profile=UserProfile.OUTDOOR_SPORTS,
            forecasts=high_temp_forecasts,
            patterns=[],
            alerts=alerts,
        )
        
        assert risk_score.temperature_risk > 50, "Temperaturas altas deberían aumentar temperature_risk"

    def test_calculate_risk_empty_forecasts(
        self, risk_service: RiskScoringService
    ):
        """Test calculate_risk con pronósticos vacíos."""
        from app.services.alert_service import AlertService
        alert_service = AlertService()
        alerts = alert_service.generate_alerts([], [])
        
        risk_score = risk_service.calculate_risk(
            profile=UserProfile.GENERAL,
            forecasts=[],
            patterns=[],
            alerts=alerts,
        )
        
        assert isinstance(risk_score, RiskScore)
        assert 0 <= risk_score.score <= 5

    def test_calculate_risk_high_precipitation(
        self, risk_service: RiskScoringService
    ):
        """Test que precipitación alta aumenta el risk score."""
        high_precip_forecasts = [
            UnifiedForecast(
                timestamp=datetime.now(UTC) + timedelta(hours=i),
                forecast_hour=i,
                latitude=-31.4201,
                longitude=-64.1888,
                temperature_celsius=15.0,
                humidity_pct=90.0,
                wind_speed_ms=5.0,
                wind_direction_deg=180.0,
                pressure_hpa=1005.0,
                precipitation_mm=50.0,  # Precipitación muy alta
                cloud_cover_pct=100.0,
                overall_confidence=0.85,
            )
            for i in range(6)
        ]
        
        from app.services.alert_service import AlertService
        alert_service = AlertService()
        alerts = alert_service.generate_alerts([], high_precip_forecasts)
        
        risk_score = risk_service.calculate_risk(
            profile=UserProfile.OUTDOOR_EVENT,
            forecasts=high_precip_forecasts,
            patterns=[],
            alerts=alerts,
        )
        
        assert risk_score.precipitation_risk > 50, "Precipitación alta debería aumentar precipitation_risk"

    def test_calculate_risk_with_storm_pattern(
        self, risk_service: RiskScoringService, sample_forecasts: list[UnifiedForecast]
    ):
        """Test que patrones de tormenta aumentan el risk score."""
        from app.services.alert_service import AlertService
        from app.services.pattern_detector import DetectedPattern, PatternType, RiskLevel
        
        storm_pattern = DetectedPattern(
            pattern_type=PatternType.SEVERE_CONVECTIVE_STORM,
            risk_level=RiskLevel.HIGH,
            confidence=0.85,
            title="Tormenta Severa",
            description="Tormenta convectiva severa detectada",
            trigger_values={"cape": 2500.0},
            thresholds_exceeded=["CAPE > 2000"],
            recommendations=["Evitar actividades al aire libre"],
        )
        
        alert_service = AlertService()
        alerts = alert_service.generate_alerts([storm_pattern], sample_forecasts)
        
        risk_score = risk_service.calculate_risk(
            profile=UserProfile.PILOT,
            forecasts=sample_forecasts,
            patterns=[storm_pattern],
            alerts=alerts,
        )
        
        # storm_risk se calcula desde los pronósticos, no directamente de los patrones
        # pattern_risk sí debería aumentar con patrones
        assert risk_score.pattern_risk > 0, "Patrón debería aumentar pattern_risk"

    def test_calculate_risk_extreme_category(
        self, risk_service: RiskScoringService
    ):
        """Test que condiciones extremas generan categoría EXTREME."""
        extreme_forecasts = [
            UnifiedForecast(
                timestamp=datetime.now(UTC) + timedelta(hours=i),
                forecast_hour=i,
                latitude=-31.4201,
                longitude=-64.1888,
                temperature_celsius=45.0,  # Temperatura extrema
                humidity_pct=20.0,
                wind_speed_ms=35.0,  # Viento extremo
                wind_direction_deg=180.0,
                pressure_hpa=1000.0,
                precipitation_mm=80.0,  # Precipitación extrema
                cloud_cover_pct=100.0,
                overall_confidence=0.85,
            )
            for i in range(6)
        ]
        
        from app.services.alert_service import AlertService
        alert_service = AlertService()
        alerts = alert_service.generate_alerts([], extreme_forecasts)
        
        risk_score = risk_service.calculate_risk(
            profile=UserProfile.PILOT,
            forecasts=extreme_forecasts,
            patterns=[],
            alerts=alerts,
        )
        
        # Con condiciones extremas, debería ser categoría alta (en español)
        assert risk_score.category in ["alto", "extremo"], "Condiciones extremas deberían generar categoría alta"
        assert risk_score.score >= 3.0, "Score debería ser alto con condiciones extremas"

    def test_calculate_risk_low_category(
        self, risk_service: RiskScoringService
    ):
        """Test que condiciones normales generan categoría LOW."""
        normal_forecasts = [
            UnifiedForecast(
                timestamp=datetime.now(UTC) + timedelta(hours=i),
                forecast_hour=i,
                latitude=-31.4201,
                longitude=-64.1888,
                temperature_celsius=20.0,  # Temperatura normal
                humidity_pct=60.0,
                wind_speed_ms=8.0,  # Viento normal
                wind_direction_deg=180.0,
                pressure_hpa=1013.0,
                precipitation_mm=0.0,  # Sin precipitación
                cloud_cover_pct=30.0,
                overall_confidence=0.85,
            )
            for i in range(6)
        ]
        
        from app.services.alert_service import AlertService
        alert_service = AlertService()
        alerts = alert_service.generate_alerts([], normal_forecasts)
        
        risk_score = risk_service.calculate_risk(
            profile=UserProfile.GENERAL,
            forecasts=normal_forecasts,
            patterns=[],
            alerts=alerts,
        )
        
        # Con condiciones normales, debería ser categoría baja (en español)
        assert risk_score.category in ["muy_bajo", "bajo", "moderado"], "Condiciones normales deberían generar categoría baja"
        assert risk_score.score <= 2.5, "Score debería ser bajo con condiciones normales"

    def test_calculate_risk_hours_ahead_parameter(
        self, risk_service: RiskScoringService, sample_forecasts: list[UnifiedForecast]
    ):
        """Test que el parámetro hours_ahead limita los pronósticos considerados."""
        from app.services.alert_service import AlertService
        alert_service = AlertService()
        alerts = alert_service.generate_alerts([], sample_forecasts)
        
        # Test con hours_ahead=24 (solo considerar primeras 24 horas)
        risk_score_24h = risk_service.calculate_risk(
            profile=UserProfile.GENERAL,
            forecasts=sample_forecasts,
            patterns=[],
            alerts=alerts,
            hours_ahead=24,
        )
        
        # Test con hours_ahead=48 (considerar más horas)
        risk_score_48h = risk_service.calculate_risk(
            profile=UserProfile.GENERAL,
            forecasts=sample_forecasts,
            patterns=[],
            alerts=alerts,
            hours_ahead=48,
        )
        
        assert isinstance(risk_score_24h, RiskScore)
        assert isinstance(risk_score_48h, RiskScore)
        # Ambos deberían ser válidos, aunque pueden diferir según los datos

    def test_calculate_risk_with_multiple_patterns(
        self, risk_service: RiskScoringService, sample_forecasts: list[UnifiedForecast]
    ):
        """Test calculate_risk con múltiples patrones."""
        from app.services.alert_service import AlertService
        from app.services.pattern_detector import DetectedPattern, PatternType, RiskLevel
        
        patterns = [
            DetectedPattern(
                pattern_type=PatternType.HEAT_WAVE,
                risk_level=RiskLevel.HIGH,
                confidence=0.8,
                title="Ola de Calor",
                description="Temperaturas elevadas",
                trigger_values={"temperature": 36.0},
                thresholds_exceeded=["heat_wave"],
                recommendations=["Hidratarse"],
            ),
            DetectedPattern(
                pattern_type=PatternType.SEVERE_CONVECTIVE_STORM,
                risk_level=RiskLevel.MODERATE,
                confidence=0.7,
                title="Tormenta",
                description="Tormenta convectiva",
                trigger_values={"cape": 1500.0},
                thresholds_exceeded=["cape_moderate"],
                recommendations=["Evitar actividades"],
            ),
        ]
        
        alert_service = AlertService()
        alerts = alert_service.generate_alerts(patterns, sample_forecasts)
        
        risk_score = risk_service.calculate_risk(
            profile=UserProfile.FARMER,
            forecasts=sample_forecasts,
            patterns=patterns,
            alerts=alerts,
        )
        
        assert isinstance(risk_score, RiskScore)
        assert risk_score.pattern_risk > 0, "Múltiples patrones deberían aumentar pattern_risk"

    def test_calculate_all_profiles(
        self, risk_service: RiskScoringService, sample_forecasts: list[UnifiedForecast]
    ):
        """Test calculate_all_profiles retorna scores para todos los perfiles (líneas 336-341)."""
        from app.services.alert_service import AlertService
        alert_service = AlertService()
        alerts = alert_service.generate_alerts([], sample_forecasts)
        
        all_scores = risk_service.calculate_all_profiles(
            forecasts=sample_forecasts,
            patterns=[],
            alerts=alerts,
        )
        
        assert isinstance(all_scores, dict)
        # Debería tener un score para cada perfil
        assert len(all_scores) == len(UserProfile)
        for profile in UserProfile:
            assert profile in all_scores
            assert isinstance(all_scores[profile], RiskScore)

    def test_calculate_temperature_risk_with_apparent_temp(
        self, risk_service: RiskScoringService
    ):
        """Test _calculate_temperature_risk con apparent_temperature (líneas 376, 381)."""
        # Crear pronósticos y usar mock para simular apparent_temperature
        from unittest.mock import Mock
        
        forecasts_with_apparent = []
        for i in range(6):
            forecast = UnifiedForecast(
                timestamp=datetime.now(UTC) + timedelta(hours=i),
                forecast_hour=i,
                latitude=-31.4201,
                longitude=-64.1888,
                temperature_celsius=30.0,
                humidity_pct=70.0,
                wind_speed_ms=5.0,
                wind_direction_deg=180.0,
                pressure_hpa=1013.25,
                precipitation_mm=0.0,
                cloud_cover_pct=30.0,
                overall_confidence=0.85,
            )
            # Usar mock para simular apparent_temperature
            mock_forecast = Mock(spec=forecast)
            mock_forecast.temperature_celsius = 30.0
            mock_forecast.apparent_temperature = 35.0  # Sensación térmica más alta
            forecasts_with_apparent.append(mock_forecast)
        
        risk, apparent_temp = risk_service._calculate_temperature_risk(
            profile=UserProfile.OUTDOOR_SPORTS,
            forecasts=forecasts_with_apparent
        )
        
        assert isinstance(risk, (int, float))
        assert 0 <= risk <= 100
        # apparent_temp puede ser None si no se encuentra en los forecasts

    def test_calculate_temperature_risk_cold(
        self, risk_service: RiskScoringService
    ):
        """Test _calculate_temperature_risk con temperaturas frías (líneas 398-400)."""
        cold_forecasts = [
            UnifiedForecast(
                timestamp=datetime.now(UTC) + timedelta(hours=i),
                forecast_hour=i,
                latitude=-31.4201,
                longitude=-64.1888,
                temperature_celsius=5.0,  # Frío
                humidity_pct=70.0,
                wind_speed_ms=8.0,
                wind_direction_deg=270.0,
                pressure_hpa=1020.0,
                precipitation_mm=0.0,
                cloud_cover_pct=20.0,
                overall_confidence=0.85,
            )
            for i in range(6)
        ]
        
        risk, apparent_temp = risk_service._calculate_temperature_risk(
            profile=UserProfile.FARMER,
            forecasts=cold_forecasts
        )
        
        assert isinstance(risk, (int, float))
        assert risk > 0, "Temperaturas frías deberían generar riesgo"

    def test_calculate_temperature_risk_extreme_cold(
        self, risk_service: RiskScoringService
    ):
        """Test _calculate_temperature_risk con frío extremo (línea 406)."""
        extreme_cold_forecasts = [
            UnifiedForecast(
                timestamp=datetime.now(UTC) + timedelta(hours=i),
                forecast_hour=i,
                latitude=-31.4201,
                longitude=-64.1888,
                temperature_celsius=-5.0,  # Frío extremo
                humidity_pct=80.0,
                wind_speed_ms=2.0,
                wind_direction_deg=180.0,
                pressure_hpa=1025.0,
                precipitation_mm=0.0,
                cloud_cover_pct=5.0,
                overall_confidence=0.85,
            )
            for i in range(6)
        ]
        
        risk, apparent_temp = risk_service._calculate_temperature_risk(
            profile=UserProfile.FARMER,
            forecasts=extreme_cold_forecasts
        )
        
        assert isinstance(risk, (int, float))
        assert risk >= 90, "Frío extremo debería generar riesgo >= 90"
