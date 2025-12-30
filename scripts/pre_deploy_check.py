#!/usr/bin/env python3
"""
Script de verificación pre-despliegue para SkyPulse.
Ejecutar antes de desplegar a producción.
"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd: list[str], description: str) -> tuple[bool, str]:
    """Ejecutar comando y retornar resultado."""
    print(f"[*] {description}...")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=300
        )
        print(f"[OK] {description} - OK")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {description} - FALLO")
        print(f"   Error: {e.stderr}")
        return False, e.stderr
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {description} - TIMEOUT")
        return False, "Timeout"


def check_imports() -> bool:
    """Verificar que no hay errores de importación."""
    print("\n📦 Verificando imports...")
    try:
        import app.api.main

        print("✅ Imports - OK")
        return True
    except ImportError as e:
        print(f"❌ Imports - FALLÓ: {e}")
        return False


def check_no_prints() -> bool:
    """Verificar que no hay print() en código de producción."""
    print("\n[*] Verificando que no hay print() en codigo...")
    app_dir = Path("app")
    if not app_dir.exists():
        print("[WARN] Directorio 'app' no encontrado")
        return False

    found_prints = []
    for py_file in app_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if "print(" in line and "#" not in line.split("print(")[0]:
                    found_prints.append(f"{py_file}:{i}")
        except Exception:
            pass

    if found_prints:
        print(f"[ERROR] Se encontraron {len(found_prints)} print() en codigo:")
        for location in found_prints[:10]:  # Mostrar solo los primeros 10
            print(f"   - {location}")
        return False

    print("[OK] No se encontraron print() en codigo")
    return True


def check_requirements() -> bool:
    """Verificar que requirements.txt existe y tiene dependencias críticas."""
    print("\n[*] Verificando requirements.txt...")
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("[ERROR] requirements.txt no encontrado")
        return False

    content = req_file.read_text()
    critical_deps = [
        "fastapi",
        "uvicorn",
        "prometheus-client",
        "pydantic",
        "requests",
    ]

    missing = []
    for dep in critical_deps:
        if dep.lower() not in content.lower():
            missing.append(dep)

    if missing:
        print(f"[ERROR] Dependencias faltantes: {', '.join(missing)}")
        return False

    print("[OK] requirements.txt - OK")
    return True


def main():
    """Ejecutar todas las verificaciones."""
    import sys
    import io

    # Configurar stdout para UTF-8 en Windows
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )

    print("=" * 60)
    print("SkyPulse - Verificacion Pre-Despliegue")
    print("=" * 60)

    checks = []

    # 1. Verificar imports
    checks.append(("Imports", check_imports()))

    # 2. Verificar que no hay print()
    checks.append(("No print()", check_no_prints()))

    # 3. Verificar requirements.txt
    checks.append(("Requirements", check_requirements()))

    # 4. Ejecutar tests
    print("\n[*] Ejecutando tests...")
    success, output = run_command(
        ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
        "Tests",
    )
    checks.append(("Tests", success))

    # 5. Verificar cobertura de módulos críticos
    print("\n[*] Verificando cobertura de modulos criticos...")
    success, output = run_command(
        [
            "python",
            "-m",
            "pytest",
            "tests/",
            "--cov=app.utils.circuit_breaker",
            "--cov=app.utils.retry",
            "--cov=app.utils.metrics",
            "--cov-report=term-missing",
            "-q",
        ],
        "Cobertura de modulos criticos",
    )
    checks.append(("Cobertura critica", success))

    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE VERIFICACIONES")
    print("=" * 60)

    all_passed = True
    for name, passed in checks:
        status = "[OK]" if passed else "[ERROR]"
        print(f"{status} {name}")

        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("[OK] Todas las verificaciones pasaron. Listo para desplegar!")
        return 0
    else:
        print("[ERROR] Algunas verificaciones fallaron. Revisar antes de desplegar.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
