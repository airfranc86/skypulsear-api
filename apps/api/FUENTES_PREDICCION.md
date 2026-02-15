# Fuentes de las predicciones – SkyPulse API

Las predicciones que expone esta API provienen de las siguientes fuentes. **El modelo WRF no se ejecuta en este servicio.**

---

## Windy (modelo GFS, el gratuito)

- **Qué es:** API Point Forecast de Windy (`https://api.windy.com/api/point-forecast/v2`).
- **Modelo usado:** **GFS** (Global Forecast System). Es el modelo gratuito/accesible con API key en Windy.
- **Uso en este servicio:** Condiciones actuales y pronóstico horario; se usa como una de las fuentes del motor de fusión.
- **Configuración:** Variable de entorno `WINDY_POINT_FORECAST_API_KEY`.  
- **Nota:** En este proyecto no se usan los modelos ECMWF ni ICON de Windy (solo GFS).

---

## WRF-SMN (datos del SMN)

- **Qué es:** Salidas del modelo WRF del **Servicio Meteorológico Nacional (SMN)** de Argentina, publicadas en AWS Open Data.
- **Cómo se usan:** Solo se **leen datos ya generados** (archivos NetCDF en el bucket `smn-ar-wrf`). **El modelo WRF no se ejecuta en este servicio.**
- **Resolución:** 4 km, inicialización 4 veces al día (00, 06, 12, 18 UTC), hasta 72 h de pronóstico.
- **Documentación:** https://registry.opendata.aws/smn-ar-wrf-dataset/

---

## Resumen

| Fuente        | Modelo | Ejecución en este servicio |
|---------------|--------|----------------------------|
| Windy         | GFS (gratuito) | No; se consume vía API      |
| WRF-SMN       | WRF 4.0 (SMN) | No; solo se ingieren datos ya publicados en S3 |

Los endpoints que usan datos en tiempo real (risk-score, alerts, patterns, **/weather/current** y **/weather/forecast**) combinan estas fuentes mediante el `UnifiedWeatherEngine` (fusión y reglas). Tras la conexión a datos reales, `/weather/current` y `/weather/forecast` provienen de las mismas fuentes: Windy (GFS/ECMWF) y/o WRF-SMN (bucket S3 SMN).
