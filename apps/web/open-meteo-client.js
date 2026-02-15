/**
 * Open-Meteo Client - API gratuita sin API key
 * Usa https://api.open-meteo.com/v1/forecast para current y hourly.
 * Documentación: https://open-meteo.com/en/docs
 */

const OPEN_METEO_BASE = 'https://api.open-meteo.com/v1/forecast';

/**
 * Construye la URL para forecast (current + hourly) en una sola petición.
 * @param {number} lat - Latitud
 * @param {number} lon - Longitud
 * @param {number} forecastDays - Días de pronóstico (1-16)
 * @returns {string} URL
 */
function buildForecastUrl(lat, lon, forecastDays) {
    const params = new URLSearchParams({
        latitude: String(lat),
        longitude: String(lon),
        current: 'temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation,weather_code,cloud_cover,surface_pressure',
        hourly: 'temperature_2m,precipitation,weather_code,wind_speed_10m',
        wind_speed_unit: 'ms',
        forecast_days: String(Math.min(16, Math.max(1, forecastDays))),
        timezone: 'auto'
    });
    return `${OPEN_METEO_BASE}?${params.toString()}`;
}

class OpenMeteoClient {
    constructor(_windyApiKey) {
        // API gratuita no usa API key; se acepta parámetro por compatibilidad con dashboard
    }

    /**
     * Obtiene tiempo actual desde Open-Meteo.
     * @param {number} lat - Latitud
     * @param {number} lon - Longitud
     * @param {string} [_model] - Ignorado (compatibilidad con llamadas del dashboard)
     * @returns {Promise<{temperature: number, humidity: number, wind_speed: number, wind_direction: number, precipitation: number, weather_code: number, cloud_cover: number, pressure: number|null, timestamp: string, source: string}>}
     */
    async getCurrentWeather(lat, lon, _model) {
        const url = buildForecastUrl(lat, lon, 1);
        const res = await fetch(url);
        if (!res.ok) {
            const err = new Error(`Open-Meteo API error: ${res.status} ${res.statusText}`);
            err.status = res.status;
            throw err;
        }
        const data = await res.json();
        const cur = data.current;
        if (!cur) {
            throw new Error('Open-Meteo: sin datos current');
        }
        return {
            temperature: cur.temperature_2m ?? 0,
            humidity: cur.relative_humidity_2m ?? 0,
            wind_speed: cur.wind_speed_10m ?? 0,
            wind_direction: cur.wind_direction_10m ?? 0,
            precipitation: cur.precipitation ?? 0,
            weather_code: cur.weather_code ?? 0,
            cloud_cover: cur.cloud_cover ?? 0,
            pressure: cur.surface_pressure != null ? cur.surface_pressure : null,
            timestamp: cur.time || new Date().toISOString(),
            source: 'open-meteo'
        };
    }

    /**
     * Obtiene pronóstico horario desde Open-Meteo.
     * @param {number} lat - Latitud
     * @param {number} lon - Longitud
     * @param {number} hoursOrDays - Horas (ej. 48) o días; se convierte a días para la API (1-16)
     * @param {string} [_model] - Ignorado (compatibilidad)
     * @returns {Promise<Array<{date: string, temperature: number, precipitation_mm: number, weather_code: number, wind_speed: number}>>}
     */
    async getHourlyForecast(lat, lon, hoursOrDays, _model) {
        const days = hoursOrDays <= 16 ? Math.max(1, Math.ceil(hoursOrDays)) : Math.min(16, Math.ceil(hoursOrDays / 24));
        const url = buildForecastUrl(lat, lon, days);
        const res = await fetch(url);
        if (!res.ok) {
            const err = new Error(`Open-Meteo API error: ${res.status} ${res.statusText}`);
            err.status = res.status;
            throw err;
        }
        const data = await res.json();
        const hourly = data.hourly;
        if (!hourly || !Array.isArray(hourly.time)) {
            throw new Error('Open-Meteo: sin datos hourly');
        }
        const times = hourly.time;
        const temps = hourly.temperature_2m || [];
        const precip = hourly.precipitation || [];
        const codes = hourly.weather_code || [];
        const wind = hourly.wind_speed_10m || [];
        return times.map((t, i) => ({
            date: t,
            temperature: temps[i] ?? 0,
            precipitation_mm: precip[i] ?? 0,
            weather_code: codes[i] ?? 0,
            wind_speed: wind[i] ?? 0
        }));
    }
}

if (typeof window !== 'undefined') {
    window.OpenMeteoClient = OpenMeteoClient;
}
