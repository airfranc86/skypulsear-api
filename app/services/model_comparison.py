"""Servicio de comparación de modelos meteorológicos."""

from typing import List, Dict, Optional
from datetime import datetime

from app.models.weather_data import WeatherData
from app.data.repositories.base_repository import IWeatherRepository
from app.services.verification import calculate_metrics, verify_multiple_variables
from app.utils.logging_config import get_logger
from app.utils.exceptions import VerificationError

logger = get_logger(__name__)


class ModelComparisonService:
    """Servicio para comparar múltiples modelos meteorológicos."""

    def __init__(self, repositories: Dict[str, IWeatherRepository]):
        """
        Inicializar servicio de comparación.

        Args:
            repositories: Diccionario con nombre de modelo como key y repository como value
        """
        self.repositories = repositories
        logger.info(
            f"ModelComparisonService inicializado con {len(repositories)} repositorios"
        )

    def compare_models_current(
        self, latitude: float, longitude: float
    ) -> Dict[str, Optional[WeatherData]]:
        """
        Comparar condiciones actuales de todos los modelos.

        Args:
            latitude: Latitud
            longitude: Longitud

        Returns:
            Diccionario con nombre de modelo como key y WeatherData como value
        """
        results = {}

        for model_name, repository in self.repositories.items():
            try:
                logger.debug(f"Obteniendo datos actuales de {model_name}")
                current_data = repository.get_current_weather(latitude, longitude)
                results[model_name] = current_data

                if current_data:
                    logger.info(f"Datos actuales obtenidos de {model_name}")
                else:
                    logger.warning(f"No se obtuvieron datos de {model_name}")

            except Exception as e:
                logger.error(f"Error obteniendo datos de {model_name}: {e}")
                results[model_name] = None

        return results

    def compare_models_forecast(
        self, latitude: float, longitude: float, hours: int = 72
    ) -> Dict[str, List[WeatherData]]:
        """
        Comparar pronósticos de todos los modelos.

        Args:
            latitude: Latitud
            longitude: Longitud
            hours: Número de horas de pronóstico

        Returns:
            Diccionario con nombre de modelo como key y lista de WeatherData como value
        """
        results = {}

        for model_name, repository in self.repositories.items():
            try:
                logger.debug(f"Obteniendo pronóstico de {model_name}")
                forecast = repository.get_forecast(latitude, longitude, hours)
                results[model_name] = forecast

                logger.info(
                    f"Pronóstico obtenido de {model_name}: {len(forecast)} puntos"
                )

            except Exception as e:
                logger.error(f"Error obteniendo pronóstico de {model_name}: {e}")
                results[model_name] = []

        return results

    def verify_models_against_observation(
        self,
        observation_data: WeatherData,
        latitude: float,
        longitude: float,
        variables: List[str],
    ) -> Dict[str, Dict[str, Dict[str, Optional[float]]]]:
        """
        Verificar todos los modelos contra una observación.

        Args:
            observation_data: Datos observados
            latitude: Latitud
            longitude: Longitud
            variables: Lista de variables a verificar

        Returns:
            Diccionario anidado: {modelo: {variable: {métrica: valor}}}
        """
        results = {}

        # Obtener datos actuales de todos los modelos
        model_data_dict = self.compare_models_current(latitude, longitude)

        for model_name, model_data in model_data_dict.items():
            if model_data is None:
                logger.warning(f"No hay datos de {model_name} para verificación")
                results[model_name] = {}
                continue

            try:
                metrics = verify_multiple_variables(
                    model_data, observation_data, variables
                )
                results[model_name] = metrics
                logger.info(f"Verificación completada para {model_name}")

            except VerificationError as e:
                logger.error(f"Error verificando {model_name}: {e}")
                results[model_name] = {}

        return results

    def get_model_summary_metrics(
        self,
        observation_data: WeatherData,
        latitude: float,
        longitude: float,
        variables: List[str],
    ) -> Dict[str, Dict[str, float]]:
        """
        Obtener métricas resumidas de todos los modelos.

        Args:
            observation_data: Datos observados
            latitude: Latitud
            longitude: Longitud
            variables: Lista de variables a analizar

        Returns:
            Diccionario con métricas promedio por modelo
        """
        verification_results = self.verify_models_against_observation(
            observation_data, latitude, longitude, variables
        )

        summary = {}

        for model_name, model_metrics in verification_results.items():
            if not model_metrics:
                continue

            # Calcular promedios de métricas
            mae_values = []
            bias_values = []
            rmse_values = []

            for variable_metrics in model_metrics.values():
                if variable_metrics.get("MAE") is not None:
                    mae_values.append(variable_metrics["MAE"])
                if variable_metrics.get("Bias") is not None:
                    bias_values.append(variable_metrics["Bias"])
                if variable_metrics.get("RMSE") is not None:
                    rmse_values.append(variable_metrics["RMSE"])

            summary[model_name] = {
                "avg_mae": sum(mae_values) / len(mae_values) if mae_values else None,
                "avg_bias": (
                    sum(bias_values) / len(bias_values) if bias_values else None
                ),
                "avg_rmse": (
                    sum(rmse_values) / len(rmse_values) if rmse_values else None
                ),
                "variables_verified": len(model_metrics),
            }

        return summary
