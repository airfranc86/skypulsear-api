"""
Tests unitarios para UnifiedWeatherEngine.

Verifica la fusión de datos meteorológicos de múltiples fuentes.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import UTC, datetime, timedelta

from app.services.unified_weather_engine import UnifiedWeatherEngine
from app.data.schemas.normalized_weather import UnifiedForecast, NormalizedWeatherData, WeatherSource
from app.data.repositories.repository_factory import RepositoryFactory


@pytest.fixture
def mock_repository_factory():
    """Fixture para crear un factory de repositorios mock."""
    factory = Mock(spec=RepositoryFactory)
    factory.repositories = {}
    factory.get_repository = Mock(return_value=None)
    factory.get_all_repositories = Mock(return_value={})
    return factory


@pytest.fixture
def unified_engine(mock_repository_factory):
    """Fixture para crear instancia de UnifiedWeatherEngine con mocks."""
    return UnifiedWeatherEngine(
        repository_factory=mock_repository_factory,
        max_workers=2
    )


@pytest.fixture
def sample_normalized_data():
    """Fixture para crear datos normalizados de ejemplo."""
    base_time = datetime.now(UTC)
    return [
        NormalizedWeatherData(
            source=WeatherSource.WINDY_GFS,
            timestamp=base_time + timedelta(hours=i),
            forecast_hour=i,
            latitude=-31.4201,
            longitude=-64.1888,
            temperature_celsius=22.0 + i * 0.5,
            humidity_pct=60.0,
            wind_speed_ms=10.0,
            wind_direction_deg=180.0,
            pressure_hpa=1013.25,
            precipitation_mm=0.0,
            cloud_cover_pct=30.0,
        )
        for i in range(6)
    ]


class TestUnifiedWeatherEngine:
    """Tests para UnifiedWeatherEngine."""

    def test_initialization(self, unified_engine: UnifiedWeatherEngine):
        """Test que el engine se inicializa correctamente."""
        assert unified_engine is not None
        assert unified_engine.normalizer is not None
        assert unified_engine.inconsistency_detector is not None
        assert unified_engine.fusion_processor is not None
        assert unified_engine.max_workers == 2

    def test_get_available_sources(self, unified_engine: UnifiedWeatherEngine):
        """Test que retorna lista de fuentes disponibles."""
        sources = unified_engine._get_available_sources()
        assert isinstance(sources, list)
        assert len(sources) > 0
        # Verificar que incluye las fuentes esperadas
        assert "windy_gfs" in sources or "wrf_smn" in sources

    def test_get_repository_none(self, unified_engine: UnifiedWeatherEngine):
        """Test que get_repository retorna None para fuente inexistente."""
        repo = unified_engine._get_repository("nonexistent_source")
        assert repo is None

    @patch('app.services.unified_weather_engine.WeatherNormalizerService')
    @patch('app.services.unified_weather_engine.WeatherFusionProcessor')
    def test_get_unified_forecast_empty_sources(
        self, mock_fusion, mock_normalizer, unified_engine: UnifiedWeatherEngine
    ):
        """Test que get_unified_forecast retorna lista vacía sin fuentes."""
        # Configurar mocks
        mock_fusion_instance = Mock()
        mock_fusion_instance.fuse.return_value = None
        unified_engine.fusion_processor = mock_fusion_instance
        
        # Llamar con fuente inexistente
        forecasts = unified_engine.get_unified_forecast(
            latitude=-31.4201,
            longitude=-64.1888,
            hours=24,
            sources=["nonexistent"]
        )
        
        assert isinstance(forecasts, list)
        # Sin repositorios válidos, debería retornar lista vacía o None

    def test_get_current_unified_none_sources(
        self, unified_engine: UnifiedWeatherEngine
    ):
        """Test que get_current_unified retorna None sin fuentes."""
        current = unified_engine.get_current_unified(
            latitude=-31.4201,
            longitude=-64.1888,
            sources=["nonexistent"]
        )
        
        # Sin repositorios válidos, debería retornar None
        assert current is None

    def test_fetch_forecast_safe_with_exception(
        self, unified_engine: UnifiedWeatherEngine
    ):
        """Test que _fetch_forecast_safe maneja excepciones correctamente."""
        # Crear repositorio mock que lanza excepción
        mock_repo = Mock()
        mock_repo.get_forecast.side_effect = Exception("Test error")
        
        # Llamar método privado usando reflection
        result = unified_engine._fetch_forecast_safe(
            mock_repo,
            latitude=-31.4201,
            longitude=-64.1888,
            hours=24,
            source="test_source"
        )
        
        # Debería retornar lista vacía en caso de error
        assert isinstance(result, list)
        assert len(result) == 0

    def test_fetch_current_safe_with_exception(
        self, unified_engine: UnifiedWeatherEngine
    ):
        """Test que _fetch_current_safe maneja excepciones correctamente."""
        # Crear repositorio mock que lanza excepción
        mock_repo = Mock()
        mock_repo.get_current_weather.side_effect = Exception("Test error")
        
        # Llamar método privado
        result = unified_engine._fetch_current_safe(
            mock_repo,
            latitude=-31.4201,
            longitude=-64.1888,
            source="test_source"
        )
        
        # Debería retornar None en caso de error
        assert result is None

    def test_group_by_forecast_hour(
        self, unified_engine: UnifiedWeatherEngine, sample_normalized_data
    ):
        """Test que _group_by_forecast_hour agrupa correctamente."""
        grouped = unified_engine._group_by_forecast_hour(sample_normalized_data)
        
        assert isinstance(grouped, dict)
        # Verificar que cada hora tiene datos
        for hour in range(6):
            assert hour in grouped
            assert len(grouped[hour]) > 0

    def test_get_repository_with_exception(
        self, unified_engine: UnifiedWeatherEngine
    ):
        """Test que _get_repository maneja excepciones correctamente."""
        # Configurar factory para lanzar excepción
        unified_engine.repository_factory.get_repository.side_effect = Exception("Test error")
        
        repo = unified_engine._get_repository("test_source")
        
        # Debería retornar None en caso de error
        assert repo is None

    def test_get_unified_forecast_with_real_data(
        self, unified_engine: UnifiedWeatherEngine, mock_repository_factory
    ):
        """Test que get_unified_forecast funciona con datos reales."""
        # Configurar mocks para retornar datos
        mock_windy_repo = Mock()
        mock_wrfsmn_repo = Mock()
        
        from app.data.repositories.base_repository import WeatherData
        base_time = datetime.now(UTC)
        
        # Mock forecast data
        mock_windy_repo.get_forecast.return_value = [
            WeatherData(
                source="windy_gfs",
                timestamp=base_time + timedelta(hours=i),
                latitude=-31.42,
                longitude=-64.19,
                temperature=280 + i,  # Kelvin
                wind_speed=5 + i,
                wind_direction=180,
                precipitation=0.1 * i,
                cloud_cover=10 + i
            ) for i in range(12)
        ]
        
        mock_wrfsmn_repo.get_forecast.return_value = [
            WeatherData(
                source="wrf_smn",
                timestamp=base_time + timedelta(hours=i),
                latitude=-31.42,
                longitude=-64.19,
                temperature=10 + i,  # Celsius
                wind_speed=3 + i,
                wind_direction=200,
                precipitation=0.05 * i,
                cloud_cover=15 + i
            ) for i in range(12)
        ]
        
        # Configurar factory
        def get_repo_side_effect(source):
            if source == "windy_gfs":
                return mock_windy_repo
            elif source == "wrf_smn":
                return mock_wrfsmn_repo
            return None
        
        unified_engine.repository_factory.get_repository.side_effect = get_repo_side_effect
        
        # Mock fusion processor
        from app.data.schemas.normalized_weather import UnifiedForecast
        mock_fusion = Mock()
        mock_fusion.fuse.return_value = UnifiedForecast(
            source=WeatherSource.FUSED,
            timestamp=base_time,
            forecast_hour=0,
            latitude=-31.42,
            longitude=-64.19,
            temperature_celsius=15.0,
            wind_speed_ms=7.0,
            wind_direction_deg=190.0,
            precipitation_mm=0.0,
            cloud_cover_pct=20.0,
            humidity_pct=75.0,
            pressure_hpa=1012.0,
            overall_confidence=0.85,
            source_breakdown={}
        )
        unified_engine.fusion_processor = mock_fusion
        
        # Llamar método
        forecasts = unified_engine.get_unified_forecast(
            latitude=-31.42,
            longitude=-64.19,
            hours=12
        )
        
        assert isinstance(forecasts, list)
        assert len(forecasts) > 0

    def test_get_current_unified_with_real_data(
        self, unified_engine: UnifiedWeatherEngine, mock_repository_factory
    ):
        """Test que get_current_unified funciona con datos reales."""
        # Configurar mocks
        mock_windy_repo = Mock()
        mock_wrfsmn_repo = Mock()
        
        from app.data.repositories.base_repository import WeatherData
        base_time = datetime.now(UTC)
        
        # Mock current weather data
        mock_windy_repo.get_current_weather.return_value = WeatherData(
            source="windy_gfs",
            timestamp=base_time,
            latitude=-31.42,
            longitude=-64.19,
            temperature=285,  # Kelvin
            wind_speed=7,
            wind_direction=190,
            precipitation=0.0,
            cloud_cover=20
        )
        
        mock_wrfsmn_repo.get_current_weather.return_value = WeatherData(
            source="wrf_smn",
            timestamp=base_time,
            latitude=-31.42,
            longitude=-64.19,
            temperature=15,  # Celsius
            wind_speed=5,
            wind_direction=210,
            precipitation=0.0,
            cloud_cover=25
        )
        
        # Configurar factory
        def get_repo_side_effect(source):
            if source == "windy_gfs":
                return mock_windy_repo
            elif source == "wrf_smn":
                return mock_wrfsmn_repo
            return None
        
        unified_engine.repository_factory.get_repository.side_effect = get_repo_side_effect
        
        # Mock fusion processor
        from app.data.schemas.normalized_weather import UnifiedForecast
        mock_fusion = Mock()
        mock_fusion.fuse.return_value = UnifiedForecast(
            source=WeatherSource.FUSED,
            timestamp=base_time,
            forecast_hour=0,
            latitude=-31.42,
            longitude=-64.19,
            temperature_celsius=15.0,
            wind_speed_ms=7.0,
            wind_direction_deg=190.0,
            precipitation_mm=0.0,
            cloud_cover_pct=20.0,
            humidity_pct=75.0,
            pressure_hpa=1012.0,
            overall_confidence=0.85,
            source_breakdown={}
        )
        unified_engine.fusion_processor = mock_fusion
        
        # Llamar método
        current = unified_engine.get_current_unified(
            latitude=-31.42,
            longitude=-64.19
        )
        
        assert current is not None
        assert isinstance(current, UnifiedForecast)

    def test_fetch_all_sources_with_data(
        self, unified_engine: UnifiedWeatherEngine
    ):
        """Test que _fetch_all_sources obtiene datos de múltiples fuentes."""
        # Configurar mocks
        mock_windy_repo = Mock()
        mock_wrfsmn_repo = Mock()
        
        from app.data.repositories.base_repository import WeatherData
        base_time = datetime.now(UTC)
        
        # Mock forecast data
        mock_windy_repo.get_forecast.return_value = [
            WeatherData(
                source="windy_gfs",
                timestamp=base_time + timedelta(hours=i),
                latitude=-31.42,
                longitude=-64.19,
                temperature=280 + i,
                wind_speed=5 + i,
                wind_direction=180,
                precipitation=0.1 * i,
                cloud_cover=10 + i
            ) for i in range(6)
        ]
        
        mock_wrfsmn_repo.get_forecast.return_value = [
            WeatherData(
                source="wrf_smn",
                timestamp=base_time + timedelta(hours=i),
                latitude=-31.42,
                longitude=-64.19,
                temperature=10 + i,
                wind_speed=3 + i,
                wind_direction=200,
                precipitation=0.05 * i,
                cloud_cover=15 + i
            ) for i in range(6)
        ]
        
        # Configurar factory
        def get_repo_side_effect(source):
            if source == "windy_gfs":
                return mock_windy_repo
            elif source == "wrf_smn":
                return mock_wrfsmn_repo
            return None
        
        unified_engine.repository_factory.get_repository.side_effect = get_repo_side_effect
        
        # Llamar método privado
        all_data = unified_engine._fetch_all_sources(
            latitude=-31.42,
            longitude=-64.19,
            hours=6,
            sources=["windy_gfs", "wrf_smn"]
        )
        
        assert isinstance(all_data, list)
        # Debería tener datos de ambas fuentes (6 horas * 2 fuentes = 12 datos)
        assert len(all_data) > 0

    def test_get_model_comparison(
        self, unified_engine: UnifiedWeatherEngine
    ):
        """Test que get_model_comparison retorna datos de cada modelo por separado."""
        # Configurar mocks
        mock_windy_repo = Mock()
        mock_wrfsmn_repo = Mock()
        
        from app.data.repositories.base_repository import WeatherData
        base_time = datetime.now(UTC)
        
        # Mock forecast data
        mock_windy_repo.get_forecast.return_value = [
            WeatherData(
                source="windy_gfs",
                timestamp=base_time + timedelta(hours=i),
                latitude=-31.42,
                longitude=-64.19,
                temperature=280 + i,
                wind_speed=5 + i,
                wind_direction=180,
                precipitation=0.1 * i,
                cloud_cover=10 + i
            ) for i in range(6)
        ]
        
        mock_wrfsmn_repo.get_forecast.return_value = [
            WeatherData(
                source="wrf_smn",
                timestamp=base_time + timedelta(hours=i),
                latitude=-31.42,
                longitude=-64.19,
                temperature=10 + i,
                wind_speed=3 + i,
                wind_direction=200,
                precipitation=0.05 * i,
                cloud_cover=15 + i
            ) for i in range(6)
        ]
        
        # Configurar factory
        def get_repo_side_effect(source):
            if source == "windy_gfs":
                return mock_windy_repo
            elif source == "wrf_smn":
                return mock_wrfsmn_repo
            return None
        
        unified_engine.repository_factory.get_repository.side_effect = get_repo_side_effect
        
        # Llamar método
        comparison = unified_engine.get_model_comparison(
            latitude=-31.42,
            longitude=-64.19,
            hours=6
        )
        
        assert isinstance(comparison, dict)
        # Debería tener datos de al menos una fuente
        assert len(comparison) > 0

    def test_fetch_all_sources_wrf_fails_windy_succeeds_fallback_gfs(
        self, unified_engine: UnifiedWeatherEngine
    ):
        """
        M1.4: Cuando WRF falla, Windy (GFS) sigue aportando datos.
        Valida fallback a GFS si WRF lanza excepción.
        """
        from app.data.repositories.base_repository import WeatherData

        base_time = datetime.now(UTC)
        windy_data = [
            WeatherData(
                source="windy_gfs",
                timestamp=base_time + timedelta(hours=i),
                latitude=-31.42,
                longitude=-64.19,
                temperature=280 + i,
                wind_speed=5 + i,
                wind_direction=180,
                precipitation=0.1 * i,
                cloud_cover=10 + i,
            )
            for i in range(6)
        ]

        mock_windy_repo = Mock()
        mock_windy_repo.get_forecast.return_value = windy_data

        mock_wrf_repo = Mock()
        mock_wrf_repo.get_forecast.side_effect = Exception("WRF S3/NetCDF no disponible")

        def get_repo_side_effect(source):
            if source == "windy_gfs":
                return mock_windy_repo
            if source == "wrf_smn":
                return mock_wrf_repo
            return None

        unified_engine.repository_factory.get_repository.side_effect = get_repo_side_effect

        all_data = unified_engine._fetch_all_sources(
            latitude=-31.42,
            longitude=-64.19,
            hours=6,
            sources=["windy_gfs", "wrf_smn"],
        )

        assert isinstance(all_data, list)
        assert len(all_data) > 0, "Debe haber datos de Windy (fallback GFS) aunque WRF falle"
        sources_in_data = {d.source for d in all_data}
        assert WeatherSource.WINDY_GFS in sources_in_data or any(
            "windy" in str(s).lower() for s in sources_in_data
        )
