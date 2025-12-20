"""Motor de Fusión Unificado - Orquestador principal."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Optional

from app.data.processors.inconsistency_detector import InconsistencyDetector
from app.data.processors.weather_fusion import WeatherFusionProcessor
from app.data.processors.weather_normalizer import WeatherNormalizerService
from app.data.repositories.repository_factory import RepositoryFactory
from app.data.schemas.normalized_weather import (
    FusionWeights,
    NormalizedWeatherData,
    UnifiedForecast,
)
from app.models.weather_data import WeatherData

logger = logging.getLogger(__name__)


class UnifiedWeatherEngine:
    """
    Motor de Fusión Unificado.
    
    Orquesta la obtención de datos de múltiples fuentes,
    normalización, detección de inconsistencias y fusión
    en un pronóstico unificado con confianza calculada.
    """
    
    def __init__(
        self,
        repository_factory: Optional[RepositoryFactory] = None,
        fusion_weights: Optional[FusionWeights] = None,
        max_workers: int = 4
    ):
        """
        Inicializa el motor de fusión.
        
        Args:
            repository_factory: Factory de repositorios (usa default si None)
            fusion_weights: Pesos de fusión personalizados
            max_workers: Número máximo de workers para fetch paralelo
        """
        self.repository_factory = repository_factory or RepositoryFactory()
        self.normalizer = WeatherNormalizerService()
        self.inconsistency_detector = InconsistencyDetector()
        self.fusion_processor = WeatherFusionProcessor(
            weights=fusion_weights,
            inconsistency_detector=self.inconsistency_detector
        )
        self.max_workers = max_workers
    
    def get_unified_forecast(
        self,
        latitude: float,
        longitude: float,
        hours: int = 72,
        sources: Optional[list[str]] = None
    ) -> list[UnifiedForecast]:
        """
        Obtiene pronóstico fusionado de múltiples fuentes.
        
        Args:
            latitude: Latitud (-90 a 90)
            longitude: Longitud (-180 a 180)
            hours: Horas de pronóstico (default 72)
            sources: Lista de fuentes a usar (None = todas disponibles)
            
        Returns:
            Lista de pronósticos fusionados por hora
        """
        logger.info(f"Obteniendo pronóstico fusionado para ({latitude}, {longitude}), {hours}h")
        
        # Determinar fuentes a usar
        available_sources = sources or self._get_available_sources()
        logger.info(f"Fuentes disponibles: {available_sources}")
        
        # Fetch paralelo de todas las fuentes
        all_data = self._fetch_all_sources(latitude, longitude, hours, available_sources)
        
        if not all_data:
            logger.warning("No se obtuvieron datos de ninguna fuente")
            return []
        
        # Agrupar datos por hora de pronóstico
        grouped_data = self._group_by_forecast_hour(all_data)
        
        # Fusionar cada hora
        unified_forecasts = []
        base_time = datetime.now(UTC)
        
        for forecast_hour in sorted(grouped_data.keys()):
            data_points = grouped_data[forecast_hour]
            
            # Calcular timestamp para esta hora
            from datetime import timedelta
            timestamp = base_time + timedelta(hours=forecast_hour)
            
            # Fusionar
            forecast = self.fusion_processor.fuse(
                data_points=data_points,
                timestamp=timestamp,
                forecast_hour=forecast_hour,
                latitude=latitude,
                longitude=longitude
            )
            
            unified_forecasts.append(forecast)
        
        logger.info(f"Generados {len(unified_forecasts)} pronósticos fusionados")
        return unified_forecasts
    
    def get_current_unified(
        self,
        latitude: float,
        longitude: float,
        sources: Optional[list[str]] = None
    ) -> Optional[UnifiedForecast]:
        """
        Obtiene condiciones actuales fusionadas.
        
        Args:
            latitude: Latitud
            longitude: Longitud
            sources: Lista de fuentes a usar
            
        Returns:
            Pronóstico fusionado para condiciones actuales
        """
        logger.info(f"Obteniendo condiciones actuales fusionadas para ({latitude}, {longitude})")
        
        available_sources = sources or self._get_available_sources()
        all_data: list[NormalizedWeatherData] = []
        
        # Fetch paralelo de datos actuales
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            for source in available_sources:
                repo = self._get_repository(source)
                if repo:
                    future = executor.submit(
                        self._fetch_current_safe,
                        repo, latitude, longitude, source
                    )
                    futures[future] = source
            
            for future in as_completed(futures):
                source = futures[future]
                try:
                    data = future.result()
                    if data:
                        all_data.append(data)
                except Exception as e:
                    logger.error(f"Error obteniendo datos actuales de {source}: {e}")
        
        if not all_data:
            return None
        
        # Fusionar
        return self.fusion_processor.fuse(
            data_points=all_data,
            timestamp=datetime.now(UTC),
            forecast_hour=0,
            latitude=latitude,
            longitude=longitude
        )
    
    def _get_available_sources(self) -> list[str]:
        """Retorna lista de fuentes disponibles."""
        # Fuentes principales según MASTER-PLAN
        return [
            "meteosource",
            "windy_ecmwf",
            "windy_gfs",
            "wrf_smn",
        ]
    
    def _get_repository(self, source: str):
        """Obtiene repositorio para una fuente."""
        try:
            return self.repository_factory.get_repository(source)
        except Exception as e:
            logger.warning(f"No se pudo obtener repositorio para {source}: {e}")
            return None
    
    def _fetch_all_sources(
        self,
        latitude: float,
        longitude: float,
        hours: int,
        sources: list[str]
    ) -> list[NormalizedWeatherData]:
        """
        Fetch paralelo de todas las fuentes.
        
        Returns:
            Lista de datos normalizados de todas las fuentes
        """
        all_data: list[NormalizedWeatherData] = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            for source in sources:
                repo = self._get_repository(source)
                if repo:
                    future = executor.submit(
                        self._fetch_forecast_safe,
                        repo, latitude, longitude, hours, source
                    )
                    futures[future] = source
            
            for future in as_completed(futures):
                source = futures[future]
                try:
                    data_list = future.result()
                    if data_list:
                        all_data.extend(data_list)
                        logger.info(f"Obtenidos {len(data_list)} registros de {source}")
                except Exception as e:
                    logger.error(f"Error obteniendo datos de {source}: {e}")
        
        return all_data
    
    def _fetch_forecast_safe(
        self,
        repo,
        latitude: float,
        longitude: float,
        hours: int,
        source: str
    ) -> list[NormalizedWeatherData]:
        """
        Fetch seguro de pronóstico con normalización.
        
        Captura excepciones y retorna lista vacía en caso de error.
        """
        try:
            # Obtener datos del repositorio
            raw_data = repo.get_forecast(latitude, longitude, hours)
            
            if not raw_data:
                return []
            
            # Normalizar
            return self.normalizer.normalize_batch(
                data_list=raw_data,
                source=source,
                latitude=latitude,
                longitude=longitude
            )
        except Exception as e:
            logger.error(f"Error en fetch_forecast de {source}: {e}")
            return []
    
    def _fetch_current_safe(
        self,
        repo,
        latitude: float,
        longitude: float,
        source: str
    ) -> Optional[NormalizedWeatherData]:
        """
        Fetch seguro de datos actuales con normalización.
        """
        try:
            raw_data = repo.get_current_weather(latitude, longitude)
            
            if not raw_data:
                return None
            
            return self.normalizer.normalize_weather_data(
                data=raw_data,
                forecast_hour=0,
                source_override=source
            )
        except Exception as e:
            logger.error(f"Error en fetch_current de {source}: {e}")
            return None
    
    def _group_by_forecast_hour(
        self,
        data: list[NormalizedWeatherData]
    ) -> dict[int, list[NormalizedWeatherData]]:
        """
        Agrupa datos por hora de pronóstico.
        
        Returns:
            Dict con forecast_hour como clave y lista de datos como valor
        """
        grouped: dict[int, list[NormalizedWeatherData]] = {}
        
        for item in data:
            hour = item.forecast_hour
            if hour not in grouped:
                grouped[hour] = []
            grouped[hour].append(item)
        
        return grouped
    
    def get_model_comparison(
        self,
        latitude: float,
        longitude: float,
        hours: int = 72
    ) -> dict[str, list[NormalizedWeatherData]]:
        """
        Obtiene datos de cada modelo por separado para comparación.
        
        Returns:
            Dict con nombre de modelo como clave y datos como valor
        """
        sources = self._get_available_sources()
        comparison: dict[str, list[NormalizedWeatherData]] = {}
        
        for source in sources:
            repo = self._get_repository(source)
            if repo:
                data = self._fetch_forecast_safe(repo, latitude, longitude, hours, source)
                if data:
                    comparison[source] = data
        
        return comparison

