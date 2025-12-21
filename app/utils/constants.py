"""Constantes del sistema SkyPulse."""

# Coordenadas por defecto (Córdoba, Argentina)
DEFAULT_LATITUDE = -31.4167
DEFAULT_LONGITUDE = -64.1833

# Ciudades predefinidas con sus coordenadas
PREDEFINED_LOCATIONS = {
    "Córdoba, Argentina": {"lat": -31.4167, "lon": -64.1833},
    "Resistencia, Argentina": {"lat": -27.4606, "lon": -58.9839},
    "Río Cuarto, Argentina": {"lat": -33.1307, "lon": -64.3499},
    "San Luis, Argentina": {"lat": -33.2950, "lon": -66.3356},
    "Buenos Aires, Argentina": {"lat": -34.6037, "lon": -58.3816},
    "Rosario, Argentina": {"lat": -32.9442, "lon": -60.6505},
    "Mendoza, Argentina": {"lat": -32.8895, "lon": -68.8458},
    "La Plata, Argentina": {"lat": -34.9215, "lon": -57.9545},
    "San Miguel de Tucumán, Argentina": {"lat": -26.8083, "lon": -65.2176},
    "Salta, Argentina": {"lat": -24.7859, "lon": -65.4117},
    "Mar del Plata, Argentina": {"lat": -38.0055, "lon": -57.5426},
}

# Variables meteorológicas
WEATHER_VARIABLES = [
    "temp",
    "viento_vel",
    "viento_dir",
    "precip",
    "nubosidad"
]

# Modelos meteorológicos soportados
SUPPORTED_MODELS = [
    "WRF-SMN",
    "ECMWF",
    "GFS",
    "Meteosource"
]

# Métricas de verificación
VERIFICATION_METRICS = [
    "MAE",      # Mean Absolute Error
    "Bias",     # Bias (sesgo)
    "RMSE",     # Root Mean Square Error
    "ETS",      # Equitable Threat Score
    "POD",      # Probability of Detection
    "FAR"       # False Alarm Rate
]

# Lead times para análisis
LEAD_TIMES = {
    "short": (0, 24),      # 0-24 horas
    "medium": (24, 72),    # 24-72 horas
    "long": (72, 168)      # 72-168 horas (3-7 días)
}

# Umbrales de alerta por defecto
DEFAULT_ALERT_THRESHOLDS = {
    "precip": 50.0,        # mm
    "viento_vel": 15.0,    # m/s
    "temp_max": 35.0,      # °C
    "temp_min": 0.0        # °C
}

# Timeout para requests HTTP (segundos)
HTTP_TIMEOUT = 30  # Aumentado para APIs externas que pueden ser lentas

# Ventana de tiempo para comparación (minutos)
COMPARISON_TIME_WINDOW = 15

