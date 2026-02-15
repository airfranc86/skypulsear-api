# 🔧 Configuración para Desarrollo Local

## 📋 Setup Inicial

### 1. Variables de Entorno

Crear archivo `.env` en la **raíz del proyecto** (mismo nivel que `apps/`):

```env
# API Keys para servicios meteorológicos
METEOSOURCE_API_KEY=tu_key_aqui
WINDY_POINT_FORECAST_API_KEY=tu_key_aqui

# API Keys válidas para autenticación
VALID_API_KEYS=demo-key,tu-api-key-real,otra-key

# Configuración general
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### 2. Backend Local

El backend ahora carga automáticamente el `.env` desde la raíz del proyecto.

**Iniciar backend**:
```powershell
cd apps\api
$env:PYTHONPATH = "."
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Verificar que carga .env**:
Deberías ver en la consola:
```
[Config] Variables de entorno cargadas desde: D:\Developer\1Proyectos\SkyPulse\.env
```

### 3. Frontend Local

**Configurar para usar backend local**:

En `apps/web/dashboard.html`, línea ~3939, cambiar:
```javascript
backendUrl: 'http://localhost:8000',  // Backend local
apiKey: "demo-key",  // Debe estar en VALID_API_KEYS del .env
```

O en `apps/web/js/api-client.js`, línea ~7:
```javascript
constructor(baseURL = 'http://localhost:8000', apiKey = null) {
```

**Iniciar frontend**:
```powershell
cd apps\web
python -m http.server 8080
```

## ✅ Verificación

### 1. Verificar que .env se carga

Al iniciar el backend, deberías ver:
```
[Config] Variables de entorno cargadas desde: ...
```

### 2. Verificar API Keys

```powershell
# Desde apps/api
$env:PYTHONPATH = "."
python -c "import os; from dotenv import load_dotenv; load_dotenv('../../.env'); print('VALID_API_KEYS:', os.getenv('VALID_API_KEYS'))"
```

### 3. Probar endpoint con API key

```powershell
$headers = @{ "X-API-Key" = "demo-key" }
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/weather/current?lat=-31.4201&lon=-64.1888" -Headers $headers
```

## 🔍 Troubleshooting

### Backend no carga .env

1. Verificar que `.env` está en la raíz del proyecto
2. Verificar que `python-dotenv` está instalado: `pip install python-dotenv`
3. Revisar logs del backend al iniciar

### API key rechazada (401)

1. Verificar que la key está en `VALID_API_KEYS` del `.env`
2. Verificar que el `.env` se carga correctamente
3. Reiniciar el backend después de cambiar `.env`

### Frontend no se conecta al backend local

1. Verificar que el backend está corriendo en `http://localhost:8000`
2. Verificar que `backendUrl` en `dashboard.html` apunta a `http://localhost:8000`
3. Verificar CORS en el backend (debe permitir `http://localhost:8080`)

## 🔄 Git Workflow

### 1. Verificar Estado

Antes de hacer commit, verificar qué archivos han cambiado:

```powershell
# Ver estado general
git status

# Ver cambios específicos (más detallado)
git status --short
```

### 2. Agregar Archivos al Staging

Agregar solo los archivos que quieres incluir en el commit:

```powershell
# Agregar archivos específicos del backend
git add apps/api/app/api/routers/weather.py
git add apps/api/app/api/routers/alerts.py
git add apps/api/app/api/routers/risk.py
git add apps/api/app/api/routers/patterns.py
git add apps/api/app/api/routers/auth.py

# O agregar todos los archivos de un directorio
git add apps/api/app/api/routers/

# O agregar todos los cambios (¡cuidado!)
git add .
```

### 3. Crear Commit

Usar mensajes descriptivos siguiendo Conventional Commits:

```powershell
# Commit con mensaje descriptivo
git commit -m "fix(api): corregir vulnerabilidades de seguridad y errores críticos

- Corregir validación de API key en endpoints de Weather
- Usar require_api_key dependency en todos los endpoints protegidos
- Corregir ruta del endpoint Patterns
- Mejorar manejo de errores: retornar 503 en lugar de 500
- Corregir endpoints de autenticación para aceptar JSON body"
```

**Tipos de commits (Conventional Commits):**
- `feat:` Nueva funcionalidad
- `fix:` Corrección de bugs
- `docs:` Cambios en documentación
- `refactor:` Refactorización de código
- `test:` Agregar o modificar tests
- `chore:` Tareas de mantenimiento

### 4. Push al Repositorio Remoto

```powershell
# Push a la rama main
git push origin main

# O si es la primera vez configurando upstream
git push -u origin main
```

### 5. Verificar Push Exitoso

```powershell
# Ver el último commit
git log -1

# Ver estado después del push
git status
```

### ⚠️ Buenas Prácticas

1. **Nunca commitees:**
   - Archivos `.env` (contienen secretos)
   - `node_modules/` (dependencias)
   - Archivos temporales o de build
   - Archivos de IDE (`.vscode/`, `.idea/`)

2. **Siempre verifica antes de commit:**
   ```powershell
   git status
   git diff  # Ver cambios en detalle
   ```

3. **Commits pequeños y frecuentes:**
   - Un commit por cambio lógico
   - Mensajes claros y descriptivos
   - No mezclar cambios no relacionados

4. **Antes de push, verifica:**
   ```powershell
   git log origin/main..HEAD  # Ver commits locales no pusheados
   ```

## 🧪 Testing

### Ejecutar Tests Unitarios

```powershell
# Desde la raíz del proyecto
cd D:\Developer\1Proyectos\SkyPulse

# Ejecutar todos los tests
pytest

# Ejecutar con cobertura
pytest --cov=app --cov-report=html --cov-report=term

# Ver reporte de cobertura en navegador
# Abrir: htmlcov/index.html
```

### Cobertura Actual

- **Cobertura promedio: 90%** (objetivo: 85%) ✅
- **PatternDetector:** 96%
- **RiskScoringService:** 84%
- **AlertService:** 88%
- **UnifiedWeatherEngine:** 94%

### TestSprite

```powershell
# Ejecutar TestSprite desde la raíz
pnpm dlx @testsprite/testsprite-mcp@latest generateCodeAndExecute

# Ver reporte generado
# Archivo: testsprite_tests/testsprite-mcp-test-report.md
```

**Estado TestSprite:**
- Tests pasando: 7/10 (70%)
- Endpoints funcionales: Health, Metrics, Weather Current, Patterns, Auth

## 📝 Notas

- El `.env` debe estar en la **raíz del proyecto**, no en `apps/api/`
- Las API keys en `VALID_API_KEYS` deben estar separadas por comas
- El backend carga el `.env` automáticamente al iniciar
- No commitees el `.env` (debe estar en `.gitignore`)
- Usa mensajes de commit descriptivos siguiendo Conventional Commits
- **Tests unitarios:** 70 tests, 90% cobertura (supera objetivo del 85%)