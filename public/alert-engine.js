/**
 * Motor de Evaluación de Alertas Meteorológicas - SkyPulse Frontend
 * 
 * Evalúa reglas declarativas contra datos de Meteosource para generar alertas.
 * Basado en la lógica de AlertService y PatternDetector del backend.
 */

class AlertEngine {
    constructor(rulesConfig) {
        this.rules = rulesConfig.rules || [];
        this.alertLevels = rulesConfig.alert_levels || {};
        this.timeWindows = rulesConfig.time_windows || {};
        this.thresholds = rulesConfig.thresholds || {};
    }

    /**
     * Evalúa pronóstico y genera alertas
     * @param {Array} forecastData - Array de datos horarios de Meteosource
     * @param {number} hoursToEvaluate - Horas a evaluar (default: 24)
     * @returns {Array} Lista de alertas generadas
     */
    evaluateForecast(forecastData, hoursToEvaluate = 24) {
        if (!forecastData || forecastData.length === 0) {
            return this._createNormalAlert();
        }

        const alerts = [];
        const currentTime = new Date();

        // Agrupar pronósticos por ventanas temporales
        const windows = this._groupByTimeWindows(forecastData, hoursToEvaluate);

        // Evaluar cada regla en cada ventana
        for (const rule of this.rules) {
            for (const [windowName, windowData] of Object.entries(windows)) {
                if (windowData.length === 0) continue;

                const alert = this._evaluateRuleInWindow(rule, windowName, windowData, currentTime);
                if (alert) {
                    alerts.push(alert);
                }
            }
        }

        // Si no hay alertas, retornar nivel normal
        if (alerts.length === 0) {
            return this._createNormalAlert();
        }

        // Eliminar duplicados y ordenar por nivel (mayor primero)
        return this._deduplicateAndSort(alerts);
    }

    /**
     * Agrupa pronósticos por ventanas temporales
     * @private
     */
    _groupByTimeWindows(forecastData, maxHours) {
        const windows = {
            "0-3h": [],
            "3-12h": [],
            "12-24h": [],
            "24-48h": []
        };

        const now = new Date();

        for (const item of forecastData) {
            const itemTime = new Date(item.date);
            const hoursFromNow = (itemTime - now) / (1000 * 60 * 60);

            if (hoursFromNow < 0 || hoursFromNow > maxHours) continue;

            if (hoursFromNow <= 3) {
                windows["0-3h"].push(item);
            } else if (hoursFromNow <= 12) {
                windows["3-12h"].push(item);
            } else if (hoursFromNow <= 24) {
                windows["12-24h"].push(item);
            } else if (hoursFromNow <= 48) {
                windows["24-48h"].push(item);
            }
        }

        return windows;
    }

    /**
     * Evalúa una regla en una ventana temporal específica
     * @private
     */
    _evaluateRuleInWindow(rule, windowName, windowData, currentTime) {
        // Extraer valores máximos/mínimos según la regla
        const values = this._extractWindowValues(windowData, rule);

        // Verificar condiciones
        if (!this._checkConditions(rule, values)) {
            return null;
        }

        // Obtener nivel de alerta para esta ventana
        const level = rule.level_by_window[windowName];
        if (!level || level === 0) {
            return null;
        }

        // Construir alerta
        const levelInfo = this.alertLevels[level.toString()];
        const windowInfo = this.timeWindows[windowName];

        return {
            level: level,
            levelName: levelInfo.name,
            phenomenon: rule.phenomenon,
            description: this._buildDescription(rule, values, windowName),
            timeWindow: windowInfo.label,
            windowName: windowName,
            recommendation: rule.recommendations[level.toString()] || this._getGenericRecommendation(level),
            triggerValues: values,
            ruleId: rule.id,
            generatedAt: currentTime.toISOString()
        };
    }

    /**
     * Extrae valores relevantes de una ventana según la regla
     * @private
     */
    _extractWindowValues(windowData, rule) {
        const values = {};

        // Extraer según condiciones de la regla
        if (rule.conditions.precipitation_mm) {
            values.precipitation_mm = Math.max(
                ...windowData.map(item => {
                    const precip = item.precipitation?.total || item.precipitation || 0;
                    return precip;
                }),
                0
            );
        }

        if (rule.conditions.wind_speed_ms) {
            values.wind_speed_ms = Math.max(
                ...windowData.map(item => {
                    const wind = item.wind?.speed || item.wind_speed || 0;
                    return wind;
                }),
                0
            );
        }

        if (rule.conditions.temperature_celsius) {
            if (rule.conditions.temperature_celsius.operator === ">=") {
                // Máximo para calor
                values.temperature_celsius = Math.max(
                    ...windowData.map(item => item.temperature || 0),
                    0
                );
            } else if (rule.conditions.temperature_celsius.operator === "<=") {
                // Mínimo para frío
                values.temperature_celsius = Math.min(
                    ...windowData.map(item => item.temperature || 100),
                    100
                );
            }
        }

        return values;
    }

    /**
     * Verifica si se cumplen las condiciones de una regla
     * @private
     */
    _checkConditions(rule, values) {
        const conditions = rule.conditions;
        const requiresAll = rule.requires_all !== false; // Default true

        let results = [];

        for (const [key, condition] of Object.entries(conditions)) {
            const value = values[key];
            if (value === undefined || value === null) {
                if (requiresAll) return false;
                continue;
            }

            const operator = condition.operator || ">=";
            let passed = false;

            if (operator === ">=") {
                passed = value >= condition.min;
            } else if (operator === "<=") {
                passed = value <= condition.max;
            } else if (operator === ">") {
                passed = value > condition.min;
            } else if (operator === "<") {
                passed = value < condition.max;
            }

            results.push(passed);
        }

        // Si requiere todas, todas deben pasar
        // Si no, al menos una debe pasar
        return requiresAll
            ? results.every(r => r === true)
            : results.some(r => r === true);
    }

    /**
     * Construye descripción de la alerta
     * @private
     */
    _buildDescription(rule, values, windowName) {
        const parts = [];

        if (values.precipitation_mm !== undefined && values.precipitation_mm > 0) {
            parts.push(`precipitación de hasta ${values.precipitation_mm.toFixed(0)}mm`);
        }

        if (values.wind_speed_ms !== undefined && values.wind_speed_ms > 0) {
            const windKmh = values.wind_speed_ms * 3.6;
            parts.push(`ráfagas de hasta ${windKmh.toFixed(0)} km/h`);
        }

        if (values.temperature_celsius !== undefined) {
            parts.push(`temperatura de ${values.temperature_celsius.toFixed(0)}°C`);
        }

        if (parts.length === 0) {
            return rule.description;
        }

        return `Condiciones adversas previstas: ${parts.join(", ")}`;
    }

    /**
     * Obtiene recomendación genérica por nivel
     * @private
     */
    _getGenericRecommendation(level) {
        const recommendations = {
            0: "Sin acción requerida.",
            1: "Monitorear actualizaciones meteorológicas.",
            2: "Evaluar planes y monitorear actualizaciones.",
            3: "Modificar o postergar actividades sensibles al clima.",
            4: "Evitar actividades al aire libre. Buscar refugio seguro."
        };

        return recommendations[level] || "Mantenerse informado.";
    }

    /**
     * Crea alerta de nivel normal
     * @private
     */
    _createNormalAlert() {
        return [{
            level: 0,
            levelName: this.alertLevels["0"].name,
            phenomenon: "condiciones estables",
            description: "Sin fenómenos meteorológicos significativos previstos.",
            timeWindow: "Próximas 24-72 horas",
            recommendation: "Sin acción requerida.",
            generatedAt: new Date().toISOString()
        }];
    }

    /**
     * Elimina duplicados y ordena alertas
     * @private
     */
    _deduplicateAndSort(alerts) {
        // Agrupar por fenómeno, mantener la de mayor nivel
        const byPhenomenon = {};

        for (const alert of alerts) {
            const key = alert.phenomenon;
            if (!byPhenomenon[key] || alert.level > byPhenomenon[key].level) {
                byPhenomenon[key] = alert;
            }
        }

        // Ordenar por nivel (mayor primero)
        return Object.values(byPhenomenon).sort((a, b) => b.level - a.level);
    }

    /**
     * Obtiene el nivel máximo de alerta
     */
    getMaxLevel(alerts) {
        if (!alerts || alerts.length === 0) return 0;
        return Math.max(...alerts.map(a => a.level));
    }
}

// Exportar para uso en módulos o global
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AlertEngine;
} else {
    window.AlertEngine = AlertEngine;
}

