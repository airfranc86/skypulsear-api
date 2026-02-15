# Deploy en Vercel – Frontend estático (apps/web)

## Qué se despliega

Solo el directorio **`apps/web/`** (HTML, JS, CSS estáticos). No se despliega backend (`apps/api/`), tests, Reportes ni el resto del monorepo.

- **Vercel** sirve el contenido de `apps/web`: `dashboard.html`, `index.html`, `investigacion-tecnica.html`, `js/`, `alert-engine.js`, etc.
- No hay build de bundling: los archivos se sirven tal cual.

---

## Deploy desde la CLI (desde tu PC)

Desde **`D:\Developer\1Proyectos\SkyPulse\apps\web`** (ya estás ahí). No hace falta build; el front es estático.

### 1. Instalar Vercel CLI (solo la primera vez)

```bash
pnpm add -g vercel
```

O con npm: `npm i -g vercel`.

### 2. Iniciar sesión (solo la primera vez)

```bash
vercel login
```

Abre el enlace que salga en el navegador y autoriza.

### 3. Enlazar con el proyecto existente (solo la primera vez en esta carpeta)

Desde `apps\web`:

```bash
vercel link
```

- **Set up and deploy?** → `Y`
- **Which scope?** → tu equipo o cuenta (ej. Franc)
- **Link to existing project?** → `Y`
- **What’s the name of your existing project?** → `skypulse-ar` (o el nombre exacto del proyecto en Vercel)

Se crea la carpeta `.vercel` con el proyecto enlazado.

### 4. Deploy

**Preview (rama/URL temporal):**

```bash
vercel
```

**Producción (skypulse-ar.vercel.app):**

```bash
vercel --prod
```

Al terminar, la CLI muestra la URL del deployment (ej. `https://skypulse-ar-xxx.vercel.app`).

### 5. Siguientes deploys

Siempre desde `D:\Developer\1Proyectos\SkyPulse\apps\web`:

```bash
vercel          # preview
vercel --prod   # producción
```

### Si estás en la raíz del repo

Desde `D:\Developer\1Proyectos\SkyPulse` puedes desplegar solo `apps/web` con:

```bash
vercel --cwd apps/web
vercel --cwd apps/web --prod
```

---

## Configuración recomendada (que funcione)

### Opción A: Root Directory = apps/web (recomendada)

1. En **Vercel** → tu proyecto → **Settings** → **General**.
2. En **Root Directory** → **Edit**.
3. Escribir exactamente: `apps/web` (sin barra inicial ni final).
4. **Save**.
5. Dejar **Build Command** vacío, o poner: `echo "static"` (para que el build no falle).
6. **Output Directory**: dejar por defecto (`.` cuando el root es `apps/web`) o en blanco.
7. **Redeploy** (Deployments → … → Redeploy).

Con esto, Vercel usa solo los archivos de `apps/web` y el [apps/web/vercel.json](apps/web/vercel.json) (rewrites, headers). La raíz del sitio es el contenido de `apps/web`.

### Opción B: Deploy desde la raíz del repo

Si no quieres usar Root Directory:

1. **Root Directory** en Vercel debe estar **vacío** (raíz del repo).
2. El [vercel.json en la raíz](vercel.json) tiene `outputDirectory: "apps/web"`, así que Vercel sirve desde esa carpeta.
3. El [.vercelignore en la raíz](.vercelignore) no debe excluir `apps/web`. No pongas `apps/web/` en `.vercelignore`.

Riesgo: Vercel puede intentar instalar dependencias desde la raíz (pnpm/npm); si el build falla, usa Opción A.

---

## Rutas y rewrites

En [apps/web/vercel.json](apps/web/vercel.json) están definidos:

- `/` → `/dashboard.html`
- `/dashboard` → `/dashboard.html`
- Headers de seguridad (X-Content-Type-Options, X-Frame-Options, etc.)
- `cleanUrls: true` (opcional)

Si al entrar a la URL del proyecto ves 404 en `/`, es que esas rewrites no se aplican: comprueba que el proyecto en Vercel tenga **Root Directory = apps/web** para que use ese `vercel.json`.

---

## Error 401 y que no actualice (crítico)

Si el sitio en Vercel carga pero **todas las peticiones al backend devuelven 401** y la página no actualiza datos (modo offline / datos de ejemplo), el fallo está en el **backend en Render**, no en Vercel.

### 1. Configurar la API key en Render (obligatorio)

1. Entra en **Render** → proyecto del backend (ej. `skypulsear-api`) → **Environment**.
2. Añade o edita la variable: **Key:** `VALID_API_KEYS`, **Value:** `skypulse-wrf-smn-aws` (exactamente la misma que usa el front en [dashboard.html](apps/web/dashboard.html) L3940).
3. **Save Changes** y haz **Manual Deploy** del servicio para que cargue la nueva variable.

### 2. Comprobar que el backend acepta la key

```bash
curl -s -H "X-API-Key: skypulse-wrf-smn-aws" "https://skypulsear-api.onrender.com/api/v1/health"
```

Si está bien, verás `"status":"ok"`. Si sale 401, la variable en Render no está bien o el deploy no se aplicó.

### 3. Comprobar que el front desplegado lleva la key

1. Abre **https://skypulse-ar.vercel.app** (o tu dominio) → F12 → Console.
2. Recarga. Deberías ver `[SkyPulse] API key configurada: skypulse-w...` y `[SkyPulseAPI] Enviando API key en header X-API-Key`.
3. Si ves `API key no configurada`, haz en Vercel **Redeploy** con **Clear Build Cache**.

### 4. Si sigue 401

- Hard refresh: Ctrl+Shift+R (o Cmd+Shift+R en Mac).
- Vercel: Redeploy con Clear Build Cache.
- Vuelve a probar el `curl` del paso 2; si sigue 401, el problema es solo en Render.

---

## Si algo no funciona

| Problema | Qué revisar |
|----------|-------------|
| **401 y no actualiza** | Ver sección anterior: `VALID_API_KEYS` en Render = `skypulse-wrf-smn-aws`, redeploy backend, luego curl y front. |
| **404 en /** o **/dashboard** | Root Directory = `apps/web` y que exista `apps/web/vercel.json` con los rewrites. Redeploy. |
| **Build falla** | Con Root Directory = `apps/web`, pon Build Command vacío o `echo "static"`. No hace falta `pnpm install` ni `npm run build` real. |
| **404 en /dashboard.html** | Comprueba que `dashboard.html` esté en la raíz de `apps/web` y que [apps/web/.vercelignore](apps/web/.vercelignore) no excluya `*.html`. |
| **JS/CSS no cargan** | Comprueba que `js/`, `alert-engine.js`, etc. no estén en `.vercelignore` dentro de `apps/web`. |
| **Botón tema (light/dark) no aparece en Vercel** | Hard refresh (Ctrl+Shift+R o Cmd+Shift+R). Si sigue sin verse: en Vercel → Deployments → … del último deploy → **Redeploy** con **Clear Build Cache**. El botón tiene estilos inline de respaldo para que sea visible aunque falle caché. |
| **Proyecto “skypulse-ar”** | Si tu proyecto tiene otro nombre, cambia solo la referencia en este doc; los pasos son los mismos. |

---

## Resumen

| Ubicación | ¿Se despliega? |
|-----------|------------------|
| `apps/web/` | Sí (frontend) |
| `apps/api/`, `app/`, tests, Reportes, etc. | No |

**Config que suele funcionar:** Root Directory = `apps/web`, Build Command vacío o `echo "static"`, Output Directory por defecto.
