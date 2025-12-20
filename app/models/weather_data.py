"""Modelos de datos meteorológicos."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class WeatherData:
    """Representa datos meteorológicos de un punto en el tiempo."""
    
    timestamp: datetime
    temperature: Optional[float] = None  # °C
    wind_speed: Optional[float] = None   # m/s
    wind_direction: Optional[float] = None  # grados (0-360)
    precipitation: Optional[float] = None  # mm
    cloud_cover: Optional[float] = None   # %
    source: Optional[str] = None  # Modelo o fuente de datos
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "temperature": self.temperature,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "precipitation": self.precipitation,
            "cloud_cover": self.cloud_cover,
            "source": self.source,
            "latitude": self.latitude,
            "longitude": self.longitude
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "WeatherData":
        """Crear desde diccionario."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        elif not isinstance(timestamp, datetime):
            raise ValueError("timestamp debe ser datetime o string ISO format")
        
        return cls(
            timestamp=timestamp,
            temperature=data.get("temperature"),
            wind_speed=data.get("wind_speed"),
            wind_direction=data.get("wind_direction"),
            precipitation=data.get("precipitation"),
            cloud_cover=data.get("cloud_cover"),
            source=data.get("source"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude")
        )

