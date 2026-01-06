/**
 * Cliente Open-Meteo para Frontend - SkyPulse
 * 
 * Obtiene datos meteorológicos desde Open-Meteo API (gratuito, sin API key).
 * Incluye fallback a Windy API si Open-Meteo falla.
 * 
 * NOTA: Open-Meteo no es ideal para Córdoba, Argentina, pero es la solución
 * temporal hasta configurar NetCDF para WRF-SMN.
 */

class OpenMeteoClient {
    constructor(windyApiKey = null) {
        this.baseUrl = 'https://api.open-meteo.com/v1/forecast';
        this.timeout = 30000; // 30 segundos
        this.windyApiKey = windyApiKey; // Para fallback
        this.windyBaseUrl = 'https://api.windy.com/api/point-forecast/v2';
    }

    /**
     * Obtiene condiciones meteorológicas actuales
     * @param {number} lat - Latitud
     * @param {number} lon - Longitud
     * @param {string} model - Modelo a usar ('ecmwf_ifs04', 'gfs_seamless', 'best_match')
     * @returns {Promise<Object>} Datos actuales
     */
    async getCurrentWeather(lat, lon, model = 'ecmwf_ifs04') {
        try {
            // Intentar Open-Meteo primero
            const data = await this._fetchOpenMeteoCurrent(lat, lon, model);
            return this._normalizeCurrentData(data, lat, lon, 'open-meteo');
        } catch (error) {
            console.warn('[Open-Meteo] Error obteniendo datos actuales, intentando fallback a Windy:', error.message);
            
            // Fallback a Windy si está configurado
            if (this.windyApiKey) {
                try {
                    return await this._fetchWindyCurrent(lat, lon);
                } catch (windyError) {
                    console.error('[Open-Meteo] Error en fallback Windy:', windyError.message);
                    throw new Error(`Open-Meteo y Windy fallaron: ${error.message}`);
                }
            }
            
            throw error;
        }
    }

    /**
     * Obtiene pronóstico horario
     * @param {number} lat - Latitud
     * @param {number} lon - Longitud
     * @param {number} hours - Horas de pronóstico (default: 48)
     * @param {string} model - Modelo a usar ('ecmwf_ifs04', 'gfs_seamless', 'best_match')
     * @returns {Promise<Array>} Array de pronósticos horarios
     */
    async getHourlyForecast(lat, lon, hours = 48, model = 'ecmwf_ifs04') {
        try {
            // Intentar Open-Meteo primero
            const data = await this._fetchOpenMeteoForecast(lat, lon, hours, model);
            return this._normalizeHourlyData(data, lat, lon, 'open-meteo');
        } catch (error) {
            console.warn('[Open-Meteo] Error obteniendo pronóstico, intentando fallback a Windy:', error.message);
            
            // Fallback a Windy si está configurado
            if (this.windyApiKey) {
                try {
                    return await this._fetchWindyForecast(lat, lon, hours);
                } catch (windyError) {
                    console.error('[Open-Meteo] Error en fallback Windy:', windyError.message);
                    throw new Error(`Open-Meteo y Windy fallaron: ${error.message}`);
                }
            }
            
            throw error;
        }
    }

    /**
     * Obtiene datos actuales desde Open-Meteo
     * @private
     */
    async _fetchOpenMeteoCurrent(lat, lon, model) {
        const params = new URLSearchParams({
            latitude: lat.toString(),
            longitude: lon.toString(),
            models: model,
            current: 'temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,weather_code,cloud_cover,pressure_msl',
            timezone: 'America/Argentina/Cordoba'
        });

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        
        const response = await fetch(`${this.baseUrl}?${params}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`Open-Meteo API error: ${response.status} ${response.statusText}`);
        }

        return await response.json();
    }

    /**
     * Obtiene pronóstico horario desde Open-Meteo
     * @private
     */
    async _fetchOpenMeteoForecast(lat, lon, hours, model) {
        // Calcular días necesarios (máximo 16 días en Open-Meteo)
        const days = Math.ceil(hours / 24);
        const forecastDays = Math.min(days, 16);

        const params = new URLSearchParams({
            latitude: lat.toString(),
            longitude: lon.toString(),
            models: model,
            hourly: 'temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,wind_gusts_10m,weather_code,cloud_cover,pressure_msl',
            timezone: 'America/Argentina/Cordoba',
            forecast_days: forecastDays.toString()
        });

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        
        const response = await fetch(`${this.baseUrl}?${params}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`Open-Meteo API error: ${response.status} ${response.statusText}`);
        }

        return await response.json();
    }

    /**
     * Obtiene datos actuales desde Windy (fallback)
     * @private
     */
    async _fetchWindyCurrent(lat, lon) {
        if (!this.windyApiKey) {
            throw new Error('Windy API key no configurada');
        }

        // Windy API requiere POST con JSON body (no GET con query params)
        const payload = {
            lat: lat,
            lon: lon,
            model: 'gfs', // Windy GFS para Argentina
            parameters: ['temp', 'dewpoint', 'precip', 'wind', 'windGust', 'pressure', 'rh', 'lclouds', 'mclouds', 'hclouds'],
            levels: ['surface'],
            key: this.windyApiKey
        };

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        
        const response = await fetch(this.windyBaseUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`Windy API error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        return this._normalizeCurrentData(data, lat, lon, 'windy-gfs');
    }

    /**
     * Obtiene pronóstico horario desde Windy (fallback)
     * @private
     */
    async _fetchWindyForecast(lat, lon, hours) {
        if (!this.windyApiKey) {
            throw new Error('Windy API key no configurada');
        }

        // Windy API requiere POST con JSON body (no GET con query params)
        const payload = {
            lat: lat,
            lon: lon,
            model: 'gfs', // Windy GFS para Argentina
            parameters: ['temp', 'dewpoint', 'precip', 'wind', 'windGust', 'pressure', 'rh', 'lclouds', 'mclouds', 'hclouds'],
            levels: ['surface'],
            key: this.windyApiKey
        };

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        
        const response = await fetch(this.windyBaseUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`Windy API error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        return this._normalizeHourlyData(data, lat, lon, 'windy-gfs');
    }

    /**
     * Normaliza datos actuales de Open-Meteo
     * @private
     */
    _normalizeCurrentData(data, lat, lon, source) {
        if (source === 'open-meteo') {
            const current = data.current || {};
            
            return {
                timestamp: current.time || new Date().toISOString(),
                temperature: current.temperature_2m,
                humidity: current.relative_humidity_2m,
                wind_speed: current.wind_speed_10m || 0, // m/s
                wind_direction: current.wind_direction_10m || 0,
                precipitation: current.precipitation || 0,
                cloud_cover: current.cloud_cover || 0,
                pressure: current.pressure_msl ? current.pressure_msl / 100 : null, // Convertir Pa a hPa
                weather_code: current.weather_code,
                latitude: lat,
                longitude: lon,
                source: source
            };
        } else if (source === 'windy-gfs') {
            // Normalizar datos de Windy (formato similar a Meteosource)
            const current = data.current || {};
            const wind = current.wind || {};
            
            return {
                timestamp: current.time || new Date().toISOString(),
                temperature: current.temperature,
                humidity: current.humidity,
                wind_speed: wind.speed || 0,
                wind_direction: wind.dir || 0,
                precipitation: current.precipitation?.total || 0,
                cloud_cover: current.cloud_cover || 0,
                pressure: current.pressure,
                weather_code: current.weather_code,
                latitude: lat,
                longitude: lon,
                source: source
            };
        }
    }

    /**
     * Normaliza datos horarios de Open-Meteo
     * @private
     */
    _normalizeHourlyData(data, lat, lon, source) {
        if (source === 'open-meteo') {
            const hourly = data.hourly || {};
            const times = hourly.time || [];
            const temperatures = hourly.temperature_2m || [];
            const humidities = hourly.relative_humidity_2m || [];
            const precipitations = hourly.precipitation || [];
            const windSpeeds = hourly.wind_speed_10m || [];
            const windDirections = hourly.wind_direction_10m || [];
            const windGusts = hourly.wind_gusts_10m || [];
            const weatherCodes = hourly.weather_code || [];
            const cloudCovers = hourly.cloud_cover || [];
            const pressures = hourly.pressure_msl || [];

            return times.map((time, index) => ({
                date: time,
                temperature: temperatures[index],
                humidity: humidities[index],
                wind: {
                    speed: windSpeeds[index] || 0,
                    dir: windDirections[index] || 0,
                    gusts: windGusts[index] || 0
                },
                wind_speed: windSpeeds[index] || 0,
                wind_direction: windDirections[index] || 0,
                wind_gusts: windGusts[index] || 0,
                precipitation: {
                    total: precipitations[index] || 0
                },
                precipitation_mm: precipitations[index] || 0,
                cloud_cover: cloudCovers[index] || 0,
                pressure: pressures[index] ? pressures[index] / 100 : null, // Convertir Pa a hPa
                weather_code: weatherCodes[index],
                latitude: lat,
                longitude: lon,
                source: source
            }));
        } else if (source === 'windy-gfs') {
            // Normalizar datos de Windy
            const hourlyData = data.hourly?.data || [];
            
            return hourlyData.map(item => {
                const wind = item.wind || {};
                const precipitation = item.precipitation || {};
                
                return {
                    date: item.date,
                    temperature: item.temperature,
                    humidity: item.humidity,
                    wind: {
                        speed: wind.speed || 0,
                        dir: wind.dir || 0
                    },
                    wind_speed: wind.speed || 0,
                    wind_direction: wind.dir || 0,
                    precipitation: {
                        total: precipitation.total || 0
                    },
                    precipitation_mm: precipitation.total || 0,
                    cloud_cover: item.cloud_cover || 0,
                    pressure: item.pressure,
                    weather_code: item.weather_code,
                    latitude: lat,
                    longitude: lon,
                    source: source
                };
            });
        }
    }
}

// Exportar para uso global
if (typeof module !== 'undefined' && module.exports) {
    module.exports = OpenMeteoClient;
} else {
    window.OpenMeteoClient = OpenMeteoClient;
}
