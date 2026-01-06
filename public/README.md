# SkyPulse Frontend v2.2

Panel de alertas meteorológicas y aviación para Argentina.

> 📍 **Lanzamiento inicial:** Datos para Córdoba, Argentina  
> 🗓️ **Última actualización:** 2026-01-04  
> 🌐 **URL Producción:** https://skypulse-ar.vercel.app/dashboard

## Estructura

```
public/
├── index.html              # Redirect → dashboard.html
├── dashboard.html          # Panel principal de riesgo meteorológico
├── aviacion-demo.html      # Demo de aviación (22 aeropuertos Argentina)
├── open-meteo-client.js    # Cliente Open-Meteo (principal) con fallback Windy
├── meteosource-client.js   # Cliente Meteosource (opcional, para alertas)
├── alert-engine.js         # Motor de alertas frontend
├── alert-rules.json        # Reglas de alertas
├── vercel.json             # Configuración Vercel
└── assets/
    ├── images/
    │   ├── logos/Logo.png
    │   ├── favicon.png
    │   └── img1.png
    └── icons/weather/       # 52 SVG icons meteorológicos
```

## Stack Técnico

### Tipografía
- **Fuente:** Inter (Google Fonts)
- **Pesos:** 300, 400, 500, 600, 700, 800

### Paleta de Colores (Windy Pro)
```css
--windy-deep-blue: #001B3C;
--windy-cyan: #00D1FF;
--windy-green-blue: #00FFBD;
--windy-yellow: #FFE600;
--windy-orange: #FF7A00;
--windy-red: #D60000;
```

### Niveles de Alerta
- **Nivel 0:** Verde (#10B981) - Normal
- **Nivel 1:** Azul (#3B82F6) - Atención
- **Nivel 2:** Amarillo (#F59E0B) - Precaución
- **Nivel 3:** Naranja (#F97316) - Alerta
- **Nivel 4:** Rojo (#DC2626) - Crítico

### Breakpoints Responsivos
- **Desktop:** > 1024px (2 columnas)
- **Tablet:** 768px - 1024px (1 columna)
- **Mobile:** < 768px (header vertical)
- **Small:** < 480px (grid compacto)

## APIs Utilizadas

### Open-Meteo (Principal - Gratuita)
- **Fuente principal** de datos meteorológicos
- Modelos: ECMWF (europeo) y GFS (global)
- Pronóstico horario hasta 48hs
- Sin API key requerida
- **NOTA:** No es ideal para Córdoba, Argentina, pero es la solución temporal hasta configurar NetCDF para WRF-SMN

### Windy (Fallback - Requiere API Key)
- **Fallback automático** si Open-Meteo falla
- Modelo: GFS (Global Forecast System)
- Solo se usa si Open-Meteo no responde
- Requiere `WINDY_API_KEY` (opcional)

### Meteosource (Opcional - Para Alertas)
- Usado para alertas si está configurado
- Si no está disponible, se usa Open-Meteo para alertas
- Requiere `METEOSOURCE_API_KEY` (opcional)

### Aviation Weather Center (AWC)
- METAR real para 22 aeropuertos Argentina
- TAF pronóstico
- Sin API key requerida

### Windy Embed
- Mapa interactivo
- Capas: viento, lluvia, temperatura
- Sin API key requerida

## Características

### Dashboard (`dashboard.html`)
- 5 niveles de alertas SkyPulse
- 11 perfiles de usuario con score de riesgo
- Mapa Windy en vivo (25% sidebar)
- Timeline deslizante 24hs
- Métricas en tiempo real

### Aviación (`aviacion-demo.html`)
- METAR/TAF real (22 aeropuertos Argentina)
- Selector de aeropuertos por región (Córdoba, Argentina)
- Cálculos aeronáuticos (Pressure Alt, Density Alt)
- Recomendación de pista con componentes de viento
- Diagrama visual de pista con rosa de vientos
- AI Briefing meteorológico
- Gráficos de temperatura y viento (Chart.js)
- Skeleton loading y toast notifications
- Orientación de pistas según AIP Argentina

## Desarrollo Local

```bash
cd public
python -m http.server 8080
# Abrir http://localhost:8080
```

## Deploy (Vercel)

**⚠️ IMPORTANTE:** El despliegue DEBE hacerse desde la carpeta `public/`, no desde la raíz del proyecto.

```bash
# Desde la carpeta public/
cd public
vercel --prod --yes
```

**URLs:**
- Producción: https://skypulse-ar.vercel.app
- Dashboard: https://skypulse-ar.vercel.app/dashboard
- Proyecto: `skypulse-ar`

**Configuración:**
- El proyecto está vinculado a `franc-projects/skypulse-ar`
- Variables de entorno opcionales en Vercel Dashboard:
  - `WINDY_API_KEY` (para fallback)
  - `METEOSOURCE_API_KEY` (para alertas)

## Idioma

Todo el frontend está en **español latinoamericano**.

## Aeropuertos Soportados (22 total)

### Córdoba Provincia (12)
| ICAO | Ciudad | Pista |
|------|--------|-------|
| SACO | Córdoba Capital | 18/36 |
| SAOC | Río Cuarto | 01/19 |
| SAOD | Villa Dolores | 01/19 |
| SACD | Coronel Olmedo | 05/23 |
| + 8 aeródromos menores |

### Argentina Principales (10)
| ICAO | Ciudad | Pista |
|------|--------|-------|
| SAEZ | Buenos Aires (Ezeiza) | 11/29 |
| SABE | Buenos Aires (Aeroparque) | 13/31 |
| SAME | Mendoza | 18/36 |
| SAAR | Rosario | 02/20 |
| SASA | Salta | 02/20 |
| SANT | Tucumán | 02/20 |
| SAZS | Bariloche | 11/29 |
| SARE | Resistencia | 07/25 |
| SAVC | Comodoro Rivadavia | 08/26 |
| SAWG | Río Gallegos | 07/25 |
| SAZN | Neuquén | 12/30 |

> Ver `.Cursor/Docs/RUNWAYS-REFERENCE.md` para datos completos de pistas.

## Roadmap

### v2.1 ✅ Completado (2025-12-18)
- [x] Selector de aeropuertos con dropdown por región
- [x] 22 aeropuertos Argentina con pistas reales
- [x] Diagrama visual de pista con rosa de vientos
- [x] Skeleton loading y toast notifications
- [x] Traducciones completas español latinoamericano

### v2.2 ✅ Completado (2026-01-04)
- [x] Integración Open-Meteo como fuente principal
- [x] Fallback automático a Windy si Open-Meteo falla
- [x] Cliente Open-Meteo con soporte ECMWF y GFS
- [x] Alertas funcionan con Open-Meteo si Meteosource no está disponible
- [x] Despliegue desde `public/` configurado correctamente

### v2.3 (Próximo)
- [ ] Configurar NetCDF para WRF-SMN (AWS S3)
- [ ] Integrar WRF-SMN como fuente principal (reemplazar Open-Meteo)
- [ ] Geolocalización automática
- [ ] Alertas push notifications

---

© 2025 SkyPulse. Todos los derechos reservados.

