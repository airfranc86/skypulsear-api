/**
 * Configuración de API Key de Meteosource - SkyPulse
 * 
 * INSTRUCCIONES:
 * 
 * Opción 1: Variable de Entorno en Vercel (RECOMENDADO para producción)
 * 1. Ir a Vercel Dashboard → Tu Proyecto → Settings → Environment Variables
 * 2. Agregar:
 *    - Key: METEOSOURCE_API_KEY
 *    - Value: Tu API key de Meteosource
 *    - Environment: Production, Preview, Development
 * 3. En vercel.json o durante el build, inyectar como window.METEOSOURCE_API_KEY
 * 
 * Opción 2: Hardcodeada en dashboard.html (SOLO para desarrollo)
 * En dashboard.html, línea ~3832, cambiar:
 *   meteosourceApiKey: null
 * Por:
 *   meteosourceApiKey: 'tu_api_key_aqui'
 * 
 * Opción 3: Archivo de configuración separado (NO commitear)
 * Crear public/config-meteosource.js con:
 *   window.METEOSOURCE_API_KEY = 'tu_api_key_aqui';
 * Y agregar antes de dashboard.html:
 *   <script src="config-meteosource.js"></script>
 * 
 * ⚠️ IMPORTANTE: NUNCA commitear la API key al repositorio
 */

// Ejemplo de configuración (NO usar en producción, solo como referencia)
// window.METEOSOURCE_API_KEY = 'tu_api_key_aqui';

