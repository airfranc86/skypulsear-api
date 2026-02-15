# Deploy en Render – API (apps/api)

## Estructura monorepo

La API está en **`apps/api/`**. El código de la app está en **`apps/api/app/`**.

---

## Si el servicio está configurado con raíz del repo (Root Directory vacío)

### Build (ya funciona con el `requirements.txt` en la raíz)

- **Build Command:** `pip install -r requirements.txt`
- El archivo **`requirements.txt`** en la raíz del repo incluye las dependencias de la API (`-r apps/api/app/requirements.txt`).

### Start (obligatorio configurarlo así)

El comando de arranque debe ejecutarse **desde** `apps/api/app/` para que el módulo `app.api.main` se resuelva bien:

- **Start Command:**  
  `cd apps/api/app && PYTHONPATH=. uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`

En Render: **Dashboard** → tu servicio (API) → **Settings** → **Build & Deploy** → **Start Command** → pegar el comando anterior → **Save Changes** → **Manual Deploy**.

---

## Opción recomendada: Root Directory = apps/api

Si prefieres que Render use solo la carpeta de la API:

1. **Dashboard** → servicio API → **Settings** → **General**.
2. **Root Directory:** `apps/api` (sin barra final).
3. **Build Command:**  
   `pip install --upgrade pip && pip install --no-cache-dir numpy>=1.26.0 && pip install --no-cache-dir -r app/requirements.txt`
4. **Start Command:**  
   `cd app && PYTHONPATH=. uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
5. **Save** y **Manual Deploy**.

Con Root Directory = `apps/api`, el build y el start se ejecutan desde `apps/api/`; no hace falta el `requirements.txt` en la raíz del repo.

---

## Resumen rápido (raíz del repo)

| Campo           | Valor |
|----------------|--------|
| **Build Command**  | `pip install -r requirements.txt` |
| **Start Command**  | `cd apps/api/app && PYTHONPATH=. uvicorn app.api.main:app --host 0.0.0.0 --port $PORT` |

Tras cambiar el Start Command, haz **Manual Deploy** para que use la nueva configuración.
