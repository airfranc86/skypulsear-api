"""Repositorio WRF-SMN funcional para SkyPulse Phase 3 - versión simplificada."""

import os
import tempfile
import logging
from typing import List, Optional, Dict, Any
from datetime import UTC, datetime, timedelta
import s3fs
import xarray as xr
import numpy as np

# Setup simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeatherData:
    """Clase simple WeatherData para WRF-SMN."""

    def __init__(
        self,
        latitude: float,
        longitude: float,
        timestamp: datetime,
        temperature: float,
        humidity: float,
        pressure: float,
        wind_speed: float,
        precipitation: float,
        **kwargs,
    ):
        self.latitude = latitude
        self.longitude = longitude
        self.timestamp = timestamp
        self.temperature = temperature
        self.humidity = humidity
        self.pressure = pressure
        self.wind_speed = wind_speed
        self.precipitation = precipitation
        self.source = kwargs.get("source", "WRF-SMN")
        self.model = kwargs.get("model", "WRF-DET")
        self.resolution = kwargs.get("resolution", "4km")


class WRFSMNRepository:
    """Repositorio WRF-SMN funcional simplificado."""

    AWS_BUCKET = "smn-ar-wrf"
    S3_PREFIX = "DATA/WRF/DET"

    def __init__(self, cache_ttl_hours: int = 6):
        self.cache_ttl_hours = cache_ttl_hours
        self._cache = {}
        self.s3_fs = self._setup_s3()

    def _setup_s3(self):
        """Configurar acceso S3 anónimo."""
        try:
            # Limpiar variables AWS forzando acceso anónimo
            aws_vars = [
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_SESSION_TOKEN",
                "AWS_PROFILE",
            ]
            old_values = {}
            for var in aws_vars:
                old_values[var] = os.environ.pop(var, None)

            try:
                fs = s3fs.S3FileSystem(anon=True)
                test_path = f"s3://{self.AWS_BUCKET}"
                if fs.exists(test_path):
                    logger.info(f"WRF-SMN S3 conectado exitosamente")
                    return fs
            finally:
                for var, value in old_values.items():
                    if value is not None:
                        os.environ[var] = value
        except Exception as e:
            logger.error(f"Error S3 WRF-SMN: {e}")
        return None

    def get_current_weather(
        self, latitude: float, longitude: float
    ) -> Optional[WeatherData]:
        """Obtener datos actuales de WRF-SMN."""
        now = datetime.now(UTC)
        init_hour = (now.hour // 6) * 6
        return self._get_from_s3(latitude, longitude, now, init_hour)

    def get_forecast(
        self, latitude: float, longitude: float, hours: int = 72
    ) -> List[WeatherData]:
        """Obtener pronóstico WRF-SMN."""
        if hours > 72:
            hours = 72

        now = datetime.now(UTC)
        init_hour = (now.hour // 6) * 6
        forecast_data = []

        for hour in range(min(hours, 72)):
            forecast_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(
                hours=hour
            )
            weather_data = self._get_from_s3(
                latitude, longitude, forecast_time, init_hour
            )
            if weather_data:
                forecast_data.append(weather_data)

        return forecast_data

    def _get_from_s3(
        self, latitude: float, longitude: float, forecast_time: datetime, init_hour: int
    ) -> Optional[WeatherData]:
        """Obtener datos desde S3."""
        if not self.s3_fs:
            return None

        # Construir ruta archivo
        init_date = forecast_time.replace(
            hour=init_hour, minute=0, second=0, microsecond=0
        )
        forecast_hour = int((forecast_time - init_date).total_seconds() / 3600)

        if forecast_hour < 0 or forecast_hour > 72:
            return None

        date_str = init_date.strftime("%Y/%m/%d/%H")
        filename = f"WRFDETAR_01H_{init_date.strftime('%Y%m%d')}_{init_hour:02d}_{forecast_hour:03d}.nc"
        s3_key = f"{self.S3_PREFIX}/{date_str}/{filename}"
        s3_path = f"s3://{self.AWS_BUCKET}/{s3_key}"

        # Verificar cache
        cache_key = f"{s3_key}_{latitude}_{longitude}"
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if (
                datetime.now() - cached_time
            ).total_seconds() < self.cache_ttl_hours * 3600:
                return cached_data

        try:
            if not self.s3_fs.exists(s3_path):
                return None

            # Descargar y procesar archivo temporalmente
            with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp_file:
                self.s3_fs.get(s3_path, tmp_file.name)

                # Intentar procesar con múltiples engines
                weather_data = self._process_netcdf(
                    tmp_file.name, latitude, longitude, forecast_time
                )

                # Cache y limpiar
                if weather_data:
                    self._cache[cache_key] = (weather_data, datetime.now())

                os.unlink(tmp_file.name)
                return weather_data

        except Exception as e:
            logger.error(f"Error procesando WRF-SMN {s3_path}: {e}")
            return None

    def _process_netcdf(
        self, filepath: str, latitude: float, longitude: float, forecast_time: datetime
    ) -> Optional[WeatherData]:
        """Procesar archivo NetCDF local."""
        engines = ["scipy", "netcdf4"]

        for engine in engines:
            try:
                with xr.open_dataset(filepath, decode_times=True, engine=engine) as ds:
                    # Verificar coordenadas
                    if "lat" not in ds.coords or "lon" not in ds.coords:
                        continue

                    lats = ds.coords["lat"].values
                    lons = ds.coords["lon"].values

                    # Encontrar punto más cercano
                    lat_diff = lats - latitude
                    lon_diff = lons - longitude
                    distance = np.sqrt(lat_diff**2 + lon_diff**2)

                    if lats.ndim == 1:  # 1D coordinates
                        lat_idx = np.abs(lats - latitude).argmin()
                        lon_idx = np.abs(lons - longitude).argmin()
                    else:  # 2D coordinates (WRF typical)
                        lat_idx, lon_idx = np.unravel_index(
                            np.argmin(distance), distance.shape
                        )

                    # Extraer variables
                    weather_dict = {}

                    # Temperatura T2
                    if "T2" in ds.data_vars:
                        temp = ds.data_vars["T2"]
                        if "time" in temp.dims:
                            temp_val = temp.isel(time=0, y=lat_idx, x=lon_idx).values
                        else:
                            temp_val = temp.isel(y=lat_idx, x=lon_idx).values
                        if temp_val > 100:  # Kelvin
                            temp_val = temp_val - 273.15
                        weather_dict["temperature"] = float(temp_val)

                    # Precipitación PP
                    if "PP" in ds.data_vars:
                        precip = ds.data_vars["PP"]
                        if "time" in precip.dims:
                            precip_val = precip.isel(
                                time=0, y=lat_idx, x=lon_idx
                            ).values
                        else:
                            precip_val = precip.isel(y=lat_idx, x=lon_idx).values
                        weather_dict["precipitation"] = float(precip_val)

                    # Humedad HR2
                    if "HR2" in ds.data_vars:
                        humidity = ds.data_vars["HR2"]
                        if "time" in humidity.dims:
                            humid_val = humidity.isel(
                                time=0, y=lat_idx, x=lon_idx
                            ).values
                        else:
                            humid_val = humidity.isel(y=lat_idx, x=lon_idx).values
                        weather_dict["humidity"] = float(humid_val)

                    # Viento magViento10
                    if "magViento10" in ds.data_vars:
                        wind = ds.data_vars["magViento10"]
                        if "time" in wind.dims:
                            wind_val = wind.isel(time=0, y=lat_idx, x=lon_idx).values
                        else:
                            wind_val = wind.isel(y=lat_idx, x=lon_idx).values
                        weather_dict["wind_speed"] = float(wind_val)

                    # Presión PSFC
                    if "PSFC" in ds.data_vars:
                        pressure = ds.data_vars["PSFC"]
                        if "time" in pressure.dims:
                            press_val = pressure.isel(
                                time=0, y=lat_idx, x=lon_idx
                            ).values
                        else:
                            press_val = pressure.isel(y=lat_idx, x=lon_idx).values
                        if press_val > 50000:  # Pa to hPa
                            press_val = press_val / 100
                        weather_dict["pressure"] = float(press_val)

                    # Validar datos mínimos y crear WeatherData
                    if "temperature" in weather_dict:
                        return WeatherData(
                            latitude=latitude,
                            longitude=longitude,
                            timestamp=forecast_time,
                            temperature=weather_dict.get("temperature", 20.0),
                            humidity=weather_dict.get("humidity", 50.0),
                            pressure=weather_dict.get("pressure", 1013.25),
                            wind_speed=weather_dict.get("wind_speed", 0.0),
                            precipitation=weather_dict.get("precipitation", 0.0),
                            source="WRF-SMN",
                            model="WRF-DET",
                            resolution="4km",
                        )

            except Exception as e:
                logger.debug(f"Engine {engine} falló: {e}")
                continue

        return None


# Test simple
def test_wrf_repository():
    """Test rápido del repositorio."""
    print("Test WRF-SMN Repository...")

    repo = WRFSMNRepository()

    # Test Córdoba
    cordoba_lat = -31.4167
    cordoba_lon = -64.1833

    print("Obteniendo datos actuales...")
    current = repo.get_current_weather(cordoba_lat, cordoba_lon)

    if current:
        print(
            f"✅ Datos actuales: T={current.temperature:.1f}°C, H={current.humidity:.1f}%"
        )
        print(f"   V={current.wind_speed:.1f}m/s, P={current.precipitation:.1f}mm")
        return True
    else:
        print("❌ No se obtuvieron datos")
        return False


if __name__ == "__main__":
    test_wrf_repository()
