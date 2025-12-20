"""Servicio de verificación de modelos meteorológicos."""

from typing import Dict, Optional
import pandas as pd

from app.models.weather_data import WeatherData
from app.utils.logging_config import get_logger
from app.utils.exceptions import VerificationError

logger = get_logger(__name__)


def calculate_mae(observed: pd.Series, predicted: pd.Series) -> Optional[float]:
    """
    Calcular Mean Absolute Error (MAE).
    
    Args:
        observed: Valores observados
        predicted: Valores predichos
    
    Returns:
        MAE o None si no hay datos suficientes
    """
    df = pd.concat([observed, predicted], axis=1).dropna()
    if df.empty:
        logger.warning("No hay datos suficientes para calcular MAE")
        return None
    
    mae = (df.iloc[:, 0] - df.iloc[:, 1]).abs().mean()
    return float(mae)


def calculate_bias(observed: pd.Series, predicted: pd.Series) -> Optional[float]:
    """
    Calcular Bias (sesgo).
    
    Bias positivo = sobreestimación
    Bias negativo = subestimación
    
    Args:
        observed: Valores observados
        predicted: Valores predichos
    
    Returns:
        Bias o None si no hay datos suficientes
    """
    df = pd.concat([observed, predicted], axis=1).dropna()
    if df.empty:
        logger.warning("No hay datos suficientes para calcular Bias")
        return None
    
    bias = (df.iloc[:, 1] - df.iloc[:, 0]).mean()
    return float(bias)


def calculate_rmse(observed: pd.Series, predicted: pd.Series) -> Optional[float]:
    """
    Calcular Root Mean Square Error (RMSE).
    
    Args:
        observed: Valores observados
        predicted: Valores predichos
    
    Returns:
        RMSE o None si no hay datos suficientes
    """
    df = pd.concat([observed, predicted], axis=1).dropna()
    if df.empty:
        logger.warning("No hay datos suficientes para calcular RMSE")
        return None
    
    mse = ((df.iloc[:, 0] - df.iloc[:, 1]) ** 2).mean()
    rmse = mse ** 0.5
    return float(rmse)


def calculate_metrics(
    observed: pd.Series,
    predicted: pd.Series
) -> Dict[str, Optional[float]]:
    """
    Calcular todas las métricas de verificación básicas.
    
    Args:
        observed: Valores observados
        predicted: Valores predichos
    
    Returns:
        Diccionario con métricas (MAE, Bias, RMSE)
    """
    return {
        "MAE": calculate_mae(observed, predicted),
        "Bias": calculate_bias(observed, predicted),
        "RMSE": calculate_rmse(observed, predicted)
    }


def verify_model_against_observation(
    model_data: WeatherData,
    observation_data: WeatherData,
    variable: str
) -> Dict[str, Optional[float]]:
    """
    Verificar un modelo contra una observación para una variable específica.
    
    Args:
        model_data: Datos del modelo
        observation_data: Datos observados
        variable: Variable a verificar (temp, viento_vel, viento_dir, precip, nubosidad)
    
    Returns:
        Diccionario con métricas de verificación
    
    Raises:
        VerificationError: Si la variable no es válida
    """
    variable_mapping = {
        "temp": ("temperature", "temperature"),
        "viento_vel": ("wind_speed", "wind_speed"),
        "viento_dir": ("wind_direction", "wind_direction"),
        "precip": ("precipitation", "precipitation"),
        "nubosidad": ("cloud_cover", "cloud_cover")
    }
    
    if variable not in variable_mapping:
        raise VerificationError(f"Variable no válida: {variable}")
    
    model_attr, obs_attr = variable_mapping[variable]
    
    model_value = getattr(model_data, model_attr)
    obs_value = getattr(observation_data, obs_attr)
    
    if model_value is None or obs_value is None:
        logger.warning(f"Valores faltantes para {variable}: model={model_value}, obs={obs_value}")
        return {"MAE": None, "Bias": None, "RMSE": None}
    
    observed_series = pd.Series([obs_value])
    predicted_series = pd.Series([model_value])
    
    return calculate_metrics(observed_series, predicted_series)


def verify_multiple_variables(
    model_data: WeatherData,
    observation_data: WeatherData,
    variables: list
) -> Dict[str, Dict[str, Optional[float]]]:
    """
    Verificar múltiples variables simultáneamente.
    
    Args:
        model_data: Datos del modelo
        observation_data: Datos observados
        variables: Lista de variables a verificar
    
    Returns:
        Diccionario con métricas por variable
    """
    results = {}
    
    for variable in variables:
        try:
            metrics = verify_model_against_observation(model_data, observation_data, variable)
            results[variable] = metrics
        except VerificationError as e:
            logger.error(f"Error verificando {variable}: {e}")
            results[variable] = {"MAE": None, "Bias": None, "RMSE": None}
    
    return results

