/**
 * Cliente API para SkyPulse
 * Consume la API FastAPI desplegada en Render
 */

class SkyPulseAPI {
    constructor(baseURL = 'https://skypulsear-api.onrender.com', apiKey = null) {
        this.baseURL = baseURL;
        this.apiKey = apiKey;
    }

    /**
     * Realiza una petición HTTP a la API con timeout
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        // Agregar API key si está disponible
        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
            console.log('[SkyPulseAPI] 🔑 Enviando API key en header X-API-Key:', this.apiKey.substring(0, 10) + '...');
        } else {
            console.warn('[SkyPulseAPI] ⚠️ API key no configurada. Las peticiones pueden fallar con 401.');
        }
        
        // Log de headers para debug (solo en desarrollo)
        if (window.location.hostname === 'localhost' || window.location.hostname.includes('127.0.0.1')) {
            console.log('[SkyPulseAPI] 📤 Headers de petición:', headers);
        }

        // Timeout por defecto: 25s (cold start Render free puede ~30s; 10s cortaba siempre)
        const timeout = options.timeout || 60000;

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            const response = await fetch(url, {
                ...options,
                headers,
                signal: controller.signal,
            });
            clearTimeout(timeoutId);

            // Manejar rate limiting
            if (response.status === 429) {
                const retryAfter = response.headers.get('Retry-After') || 60;
                throw new Error(`Rate limit excedido. Intente nuevamente en ${retryAfter} segundos.`);
            }

            // Manejar errores HTTP
            if (!response.ok) {
                // Log detallado para errores 401
                if (response.status === 401) {
                    console.error('[SkyPulseAPI] ❌ Error 401 - Unauthorized');
                    console.error('[SkyPulseAPI] 📤 Headers enviados:', headers);
                    console.error('[SkyPulseAPI] 🔑 API key en cliente:', this.apiKey ? this.apiKey.substring(0, 10) + '...' : 'NO CONFIGURADA');
                    console.error('[SkyPulseAPI] 🌐 URL:', url);
                }
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                const err = new Error(error.detail || `Error ${response.status}: ${response.statusText}`);
                err.status = response.status;
                throw err;
            }

            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                const timeoutErr = new Error(`Timeout: La petición excedió ${timeout / 1000} segundos`);
                timeoutErr.name = 'AbortError';
                console.error('[SkyPulseAPI]', timeoutErr.message);
                throw timeoutErr;
            }
            console.error('Error en petición API:', error);
            throw error;
        }
    }

    /**
     * Health check
     */
    async healthCheck() {
        return this.request('/health');
    }

    /**
     * Obtiene datos meteorológicos actuales
     */
    async getCurrentWeather(lat, lon) {
        return this.request(`/api/v1/weather/current?lat=${lat}&lon=${lon}`);
    }

    /**
     * Obtiene pronóstico meteorológico
     */
    async getForecast(lat, lon, hours = 24) {
        return this.request(`/api/v1/weather/forecast?lat=${lat}&lon=${lon}&hours=${hours}`);
    }

    /**
     * Calcula risk score para un perfil
     */
    async calculateRiskScore(lat, lon, profile, hoursAhead = 6) {
        return this.request('/api/v1/risk-score', {
            method: 'POST',
            body: JSON.stringify({
                lat,
                lon,
                profile,
                hours_ahead: hoursAhead,
            }),
        });
    }

    /**
     * Obtiene alertas meteorológicas
     */
    async getAlerts(lat, lon, hours = 24) {
        return this.request(`/api/v1/alerts?lat=${lat}&lon=${lon}&hours=${hours}`);
    }

    /**
     * Obtiene alertas meteorológicas (weather endpoint)
     */
    async getWeatherAlerts(lat, lon, hours = 24) {
        return this.request(`/api/v1/weather/alerts?lat=${lat}&lon=${lon}&hours=${hours}&api_key=${this.apiKey || 'demo-key'}`);
    }

    /**
     * Obtiene patrones meteorológicos detectados
     */
    async getPatterns(lat, lon, hours = 72) {
        return this.request(`/api/v1/patterns?lat=${lat}&lon=${lon}&hours=${hours}`);
    }

    /**
     * Obtiene tipos de patrones disponibles
     */
    async getPatternTypes() {
        return this.request('/api/v1/patterns/types');
    }

    /**
     * Obtiene categoría de vuelo OMM/OHMC (VFR/MVFR/IFR/LIFR) para lat/lon (M3.2).
     */
    async getFlightCategory(lat, lon) {
        return this.request(`/api/v1/weather/flight-category?lat=${lat}&lon=${lon}`);
    }
}

// Exportar para uso global
window.SkyPulseAPI = SkyPulseAPI;

