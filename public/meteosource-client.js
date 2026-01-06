/**
 * Cliente Meteosource para Frontend - SkyPulse
 * 
 * Obtiene datos meteorológicos directamente desde Meteosource API.
 * Reemplaza llamadas al backend para enfoque frontend-only.
 */

class MeteosourceClient {
    constructor(apiKey) {
        if (!apiKey) {
            throw new Error('METEOSOURCE_API_KEY es requerida');
        }
        this.apiKey = apiKey;
        this.baseUrl = 'https://api.meteosource.com/v1/flexi';
        this.timeout = 30000; // 30 segundos
    }

    /**
     * Obtiene condiciones meteorológicas actuales
     * @param {number} lat - Latitud
     * @param {number} lon - Longitud
     * @returns {Promise<Object>} Datos actuales
     */
    async getCurrentWeather(lat, lon) {
        try {
            const url = `${this.baseUrl}/point`;
            const params = new URLSearchParams({
                lat: lat.toString(),
                lon: lon.toString(),
                key: this.apiKey,
                sections: 'current',
                units: 'metric',
                lang: 'es'
            });

            // Crear AbortController para timeout (compatible con navegadores más antiguos)
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);
            
            const response = await fetch(`${url}?${params}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`Meteosource API error: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            return this._normalizeCurrentData(data, lat, lon);
        } catch (error) {
            console.error('[Meteosource] Error obteniendo datos actuales:', error);
            throw error;
        }
    }

    /**
     * Obtiene pronóstico horario
     * @param {number} lat - Latitud
     * @param {number} lon - Longitud
     * @param {number} hours - Horas de pronóstico (default: 48)
     * @returns {Promise<Array>} Array de pronósticos horarios
     */
    async getHourlyForecast(lat, lon, hours = 48) {
        try {
            const url = `${this.baseUrl}/point`;
            const params = new URLSearchParams({
                lat: lat.toString(),
                lon: lon.toString(),
                key: this.apiKey,
                sections: 'hourly',
                units: 'metric',
                lang: 'es'
            });

            // Crear AbortController para timeout (compatible con navegadores más antiguos)
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);
            
            const response = await fetch(`${url}?${params}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`Meteosource API error: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            const hourlyData = data.hourly?.data || [];
            
            // Limitar a las horas solicitadas
            const limited = hourlyData.slice(0, hours);
            
            return limited.map(item => this._normalizeHourlyData(item, lat, lon));
        } catch (error) {
            console.error('[Meteosource] Error obteniendo pronóstico:', error);
            throw error;
        }
    }

    /**
     * Normaliza datos actuales de Meteosource
     * @private
     */
    _normalizeCurrentData(data, lat, lon) {
        const current = data.current || {};
        const wind = current.wind || {};
        const precipitation = current.precipitation || {};

        return {
            timestamp: current.time || new Date().toISOString(),
            temperature: current.temperature,
            humidity: current.humidity,
            wind_speed: wind.speed, // m/s
            wind_direction: wind.dir,
            precipitation: precipitation.total || 0,
            cloud_cover: current.cloud_cover,
            pressure: current.pressure,
            weather_code: current.weather_code,
            latitude: lat,
            longitude: lon,
            source: 'meteosource'
        };
    }

    /**
     * Normaliza datos horarios de Meteosource
     * @private
     */
    _normalizeHourlyData(item, lat, lon) {
        const wind = item.wind || {};
        const precipitation = item.precipitation || {};

        return {
            date: item.date,
            temperature: item.temperature,
            humidity: item.humidity,
            wind: {
                speed: wind.speed, // m/s
                dir: wind.dir
            },
            wind_speed: wind.speed, // Compatibilidad
            wind_direction: wind.dir,
            precipitation: {
                total: precipitation.total || 0
            },
            precipitation_mm: precipitation.total || 0, // Compatibilidad
            cloud_cover: item.cloud_cover,
            pressure: item.pressure,
            weather_code: item.weather_code,
            latitude: lat,
            longitude: lon
        };
    }
}

// Exportar para uso global
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MeteosourceClient;
} else {
    window.MeteosourceClient = MeteosourceClient;
}

