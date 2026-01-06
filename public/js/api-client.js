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
        }

        // Timeout por defecto: 10 segundos
        const timeout = options.timeout || 10000;

        try {
            // Crear promesa con timeout
            const fetchPromise = fetch(url, {
                ...options,
                headers,
            });

            const timeoutPromise = new Promise((_, reject) => {
                setTimeout(() => {
                    reject(new Error(`Timeout: La petición excedió ${timeout / 1000} segundos`));
                }, timeout);
            });

            const response = await Promise.race([fetchPromise, timeoutPromise]);

            // Manejar rate limiting
            if (response.status === 429) {
                const retryAfter = response.headers.get('Retry-After') || 60;
                throw new Error(`Rate limit excedido. Intente nuevamente en ${retryAfter} segundos.`);
            }

            // Manejar errores HTTP
            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(error.detail || `Error ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
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
}

// Exportar para uso global
window.SkyPulseAPI = SkyPulseAPI;

