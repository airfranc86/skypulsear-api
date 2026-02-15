/**
 * Meteosource Client - Stub para desarrollo local
 * NOTA: Este es un stub mínimo. El archivo completo está en el repo skypulse-front
 */

class MeteosourceClient {
    constructor(apiKey = null) {
        this.apiKey = apiKey;
        console.warn('[MeteosourceClient] Stub en uso - funcionalidad limitada');
    }

    async getCurrentWeather(lat, lon) {
        console.warn('[MeteosourceClient] getCurrentWeather - stub');
        return null;
    }

    async getForecast(lat, lon) {
        console.warn('[MeteosourceClient] getForecast - stub');
        return null;
    }
}

// Exportar para uso global
if (typeof window !== 'undefined') {
    window.MeteosourceClient = MeteosourceClient;
}
