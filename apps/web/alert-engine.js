/**
 * Alert Engine - Stub para desarrollo local
 * NOTA: Este es un stub mínimo. El archivo completo está en el repo skypulse-front
 */

class AlertEngine {
    constructor() {
        this.rules = [];
        console.warn('[AlertEngine] Stub en uso - funcionalidad limitada');
    }

    async loadRules() {
        console.warn('[AlertEngine] loadRules - stub');
        return [];
    }

    evaluateAlerts(weatherData) {
        console.warn('[AlertEngine] evaluateAlerts - stub');
        return [];
    }
}

// Exportar para uso global
if (typeof window !== 'undefined') {
    window.AlertEngine = AlertEngine;
}
