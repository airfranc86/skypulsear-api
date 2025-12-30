# Solución: Error de compilación netCDF4 en Render

## Problema

```
ModuleNotFoundError: No module named 'numpy'
error: metadata-generation-failed
```

`netCDF4` necesita `numpy` instalado **antes** de compilarse, pero el entorno de build aislado no lo encuentra.

## Solución Aplicada

El `buildCommand` en `render.yaml` ha sido actualizado:

```yaml
buildCommand: |
  apt-get update && apt-get install -y libhdf5-dev libnetcdf-dev && \
  pip install --upgrade pip setuptools wheel && \
  pip install --no-cache-dir numpy>=1.26.0 && \
  python -c "import numpy; print(f'NumPy version: {numpy.__version__}')" && \
  pip install --no-cache-dir --no-build-isolation netCDF4>=1.6.0 && \
  pip install --no-cache-dir -r requirements.txt
```

### Cambios clave:

1. **`--no-build-isolation`**: Permite que netCDF4 vea numpy ya instalado
2. **Verificación de numpy**: Confirma que numpy está instalado antes de netCDF4
3. **`setuptools wheel`**: Asegura herramientas de build actualizadas

## Si el error persiste

### Opción 1: Usar wheel precompilado (más rápido)

Si Render tiene wheels precompilados disponibles, puedes intentar:

```yaml
buildCommand: |
  apt-get update && apt-get install -y libhdf5-dev libnetcdf-dev && \
  pip install --upgrade pip && \
  pip install --no-cache-dir numpy>=1.26.0 && \
  pip install --only-binary=netCDF4 netCDF4>=1.6.0 && \
  pip install --no-cache-dir -r requirements.txt
```

### Opción 2: Remover netCDF4 (si no se usa WRF-SMN)

Si no estás usando WRF-SMN, puedes remover netCDF4:

1. **Comentar en `requirements.txt`:**
   ```txt
   # netCDF4>=1.6.0
   # xarray>=2023.1.0
   # s3fs>=2023.1.0
   ```

2. **Simplificar build command:**
   ```yaml
   buildCommand: |
     pip install --upgrade pip && \
     pip install -r requirements.txt
   ```

### Opción 3: Usar Python 3.12 explícitamente

Render puede estar usando Python 3.13 por defecto. Asegurar Python 3.12:

1. **En Render Dashboard:**
   - Environment → `PYTHON_VERSION` = `3.12`

2. **O en `render.yaml` (ya configurado):**
   ```yaml
   envVars:
     - key: PYTHON_VERSION
       value: "3.12"
   ```

## Verificación

Después del despliegue, verificar que netCDF4 está instalado:

```bash
# En Render logs o agregar endpoint temporal:
@app.get("/debug/deps")
async def debug_deps():
    try:
        import netCDF4
        import numpy
        return {
            "netCDF4": netCDF4.__version__,
            "numpy": numpy.__version__,
            "status": "OK"
        }
    except ImportError as e:
        return {"error": str(e)}
```

## Referencias

- [netCDF4-python Installation](https://unidata.github.io/netcdf4-python/)
- [Render Build Environment](https://render.com/docs/build-environment)

