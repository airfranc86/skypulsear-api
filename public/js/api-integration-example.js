/**
 * Ejemplo de integración del cliente API con el dashboard
 * Este archivo muestra cómo usar SkyPulseAPI en el dashboard
 */

// Ejemplo 1: Cargar datos meteorológicos actuales
async function loadCurrentWeather() {
    try {
        const data = await api.getCurrentWeather(
            CONFIG.location.lat,
            CONFIG.location.lon
        );

        // Actualizar UI con datos
        updateWeatherDisplay(data);
    } catch (error) {
        console.error('Error cargando datos meteorológicos:', error);
        showError('No se pudieron cargar los datos meteorológicos');
    }
}

// Ejemplo 2: Calcular risk score para un perfil
async function calculateRiskForProfile(profile) {
    try {
        const result = await api.calculateRiskScore(
            CONFIG.location.lat,
            CONFIG.location.lon,
            profile,
            6 // horas a evaluar
        );

        // Mostrar resultado
        displayRiskScore(result);
    } catch (error) {
        console.error('Error calculando risk score:', error);
        showError('No se pudo calcular el riesgo');
    }
}

// Ejemplo 3: Obtener alertas
async function loadAlerts() {
    try {
        const alerts = await api.getAlerts(
            CONFIG.location.lat,
            CONFIG.location.lon,
            24 // próximas 24 horas
        );

        // Mostrar alertas en UI
        displayAlerts(alerts);
    } catch (error) {
        console.error('Error cargando alertas:', error);
    }
}

// Ejemplo 4: Obtener patrones detectados
async function loadPatterns() {
    try {
        const patterns = await api.getPatterns(
            CONFIG.location.lat,
            CONFIG.location.lon,
            72 // próximas 72 horas
        );

        // Mostrar patrones
        displayPatterns(patterns);
    } catch (error) {
        console.error('Error cargando patrones:', error);
    }
}

// Ejemplo 5: Cargar pronóstico completo
async function loadFullForecast() {
    try {
        const forecast = await api.getForecast(
            CONFIG.location.lat,
            CONFIG.location.lon,
            48 // próximas 48 horas
        );

        // Actualizar gráficos y timeline
        updateForecastCharts(forecast);
    } catch (error) {
        console.error('Error cargando pronóstico:', error);
    }
}

// Función helper para manejar errores de rate limiting
function handleRateLimitError(error) {
    if (error.message.includes('Rate limit')) {
        const retryAfter = error.message.match(/(\d+) segundos/)?.[1] || 60;
        showNotification(
            `Rate limit excedido. Esperando ${retryAfter} segundos...`,
            'warning'
        );
        setTimeout(() => {
            // Reintentar después del tiempo especificado
            location.reload();
        }, retryAfter * 1000);
    }
}

