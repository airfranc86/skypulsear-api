"""
Script para descargar iconos personalizados desde yesicon.app/iconify.

Descarga iconos específicos de diferentes colecciones:
- mdi: Material Design Icons (7447 iconos disponibles)
- svg-spinners: SVG Spinners (46 iconos disponibles)
"""

import requests
from pathlib import Path
import time
from typing import List, Tuple, Optional

BASE_DIR = Path(__file__).parent.parent
CUSTOM_DIR = BASE_DIR / "static" / "icons" / "custom"
SVGSPINNER_DIR = BASE_DIR / "static" / "icons" / "SVGSpinner"

# Crear directorios si no existen
CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
SVGSPINNER_DIR.mkdir(parents=True, exist_ok=True)

# Iconos MDI (Material Design Icons) para custom/
# Basado en https://yesicon.app/mdi (7447 iconos disponibles)
MDI_ICONS: List[Tuple[str, str, str]] = [
    # (collection, icon_name, description)
    # Cuenta y usuario
    ("mdi", "account", "Cuenta"),
    ("mdi", "account-circle", "Cuenta círculo"),
    ("mdi", "account-circle-outline", "Cuenta círculo contorno"),
    ("mdi", "account-outline", "Cuenta contorno"),
    ("mdi", "account-multiple", "Cuentas múltiples"),
    ("mdi", "account-multiple-outline", "Cuentas múltiples contorno"),
    # Alertas y notificaciones
    ("mdi", "alert", "Alerta"),
    ("mdi", "alert-circle", "Alerta círculo"),
    ("mdi", "alert-circle-outline", "Alerta círculo contorno"),
    ("mdi", "alert-outline", "Alerta contorno"),
    ("mdi", "bell", "Campana"),
    ("mdi", "bell-outline", "Campana contorno"),
    ("mdi", "bell-ring", "Campana sonando"),
    ("mdi", "bell-ring-outline", "Campana sonando contorno"),
    # Navegación
    ("mdi", "arrow-left", "Flecha izquierda"),
    ("mdi", "arrow-right", "Flecha derecha"),
    ("mdi", "arrow-up", "Flecha arriba"),
    ("mdi", "arrow-down", "Flecha abajo"),
    ("mdi", "refresh", "Refrescar"),
    ("mdi", "refresh-circle", "Refrescar círculo"),
    # Estado y acciones
    ("mdi", "check", "Check"),
    ("mdi", "check-circle", "Check círculo"),
    ("mdi", "check-circle-outline", "Check círculo contorno"),
    ("mdi", "close", "Cerrar"),
    ("mdi", "close-circle", "Cerrar círculo"),
    ("mdi", "close-circle-outline", "Cerrar círculo contorno"),
    # Archivos y documentos
    ("mdi", "file-document", "Documento"),
    ("mdi", "file-document-outline", "Documento contorno"),
    ("mdi", "file-download", "Descargar"),
    ("mdi", "file-download-outline", "Descargar contorno"),
    ("mdi", "file-upload", "Subir"),
    ("mdi", "file-upload-outline", "Subir contorno"),
    ("mdi", "folder", "Carpeta"),
    ("mdi", "folder-outline", "Carpeta contorno"),
    # Gráficos y datos
    ("mdi", "chart-line", "Gráfico línea"),
    ("mdi", "chart-bar", "Gráfico barras"),
    ("mdi", "chart-pie", "Gráfico circular"),
    ("mdi", "chart-box", "Gráfico caja"),
    ("mdi", "chart-box-outline", "Gráfico caja contorno"),
    # Ubicación y mapas
    ("mdi", "map", "Mapa"),
    ("mdi", "map-marker", "Marcador mapa"),
    ("mdi", "map-marker-outline", "Marcador mapa contorno"),
    ("mdi", "map-marker-radius", "Marcador mapa radio"),
    ("mdi", "map-marker-radius-outline", "Marcador mapa radio contorno"),
    # Tiempo y calendario
    ("mdi", "calendar", "Calendario"),
    ("mdi", "calendar-outline", "Calendario contorno"),
    ("mdi", "clock", "Reloj"),
    ("mdi", "clock-outline", "Reloj contorno"),
    ("mdi", "clock-time-four", "Reloj hora cuatro"),
    ("mdi", "clock-time-four-outline", "Reloj hora cuatro contorno"),
    # Clima (complemento a Weather Icons)
    ("mdi", "weather-cloudy", "Clima nublado"),
    ("mdi", "weather-rainy", "Clima lluvioso"),
    ("mdi", "weather-sunny", "Clima soleado"),
    ("mdi", "weather-partly-cloudy", "Clima parcialmente nublado"),
    ("mdi", "weather-lightning", "Clima relámpago"),
    ("mdi", "weather-snowy", "Clima nevado"),
    ("mdi", "thermometer", "Termómetro"),
    # Búsqueda y filtros
    ("mdi", "magnify", "Búsqueda"),
    ("mdi", "magnify-outline", "Búsqueda contorno"),
    ("mdi", "filter", "Filtro"),
    ("mdi", "filter-outline", "Filtro contorno"),
    # Configuración
    ("mdi", "cog", "Configuración"),
    ("mdi", "cog-outline", "Configuración contorno"),
    ("mdi", "settings", "Ajustes"),
    ("mdi", "settings-outline", "Ajustes contorno"),
    # Información
    ("mdi", "information", "Información"),
    ("mdi", "information-outline", "Información contorno"),
    ("mdi", "help-circle", "Ayuda círculo"),
    ("mdi", "help-circle-outline", "Ayuda círculo contorno"),
    # Acciones
    ("mdi", "pencil", "Editar"),
    ("mdi", "pencil-outline", "Editar contorno"),
    ("mdi", "delete", "Eliminar"),
    ("mdi", "delete-outline", "Eliminar contorno"),
    ("mdi", "plus", "Agregar"),
    ("mdi", "plus-circle", "Agregar círculo"),
    ("mdi", "plus-circle-outline", "Agregar círculo contorno"),
    ("mdi", "minus", "Quitar"),
    ("mdi", "minus-circle", "Quitar círculo"),
    ("mdi", "minus-circle-outline", "Quitar círculo contorno"),
    # Interfaz
    ("mdi", "menu", "Menú"),
    ("mdi", "home", "Inicio"),
    ("mdi", "home-outline", "Inicio contorno"),
    ("mdi", "logout", "Cerrar sesión"),
    ("mdi", "logout-variant", "Cerrar sesión variante"),
]

# Iconos SVG Spinners para SVGSpinner/
# Basado en https://yesicon.app/svg-spinners (46 iconos disponibles)
SVG_SPINNERS_ICONS: List[Tuple[str, str, str]] = [
    # (collection, icon_name, description)
    # Dots (puntos)
    ("svg-spinners", "3-dots-scale", "3 puntos escala"),
    ("svg-spinners", "3-dots-bounce", "3 puntos rebote"),
    ("svg-spinners", "3-dots-fade", "3 puntos desvanecer"),
    ("svg-spinners", "3-dots-move", "3 puntos mover"),
    ("svg-spinners", "3-dots-rotate", "3 puntos rotar"),
    ("svg-spinners", "3-dots-scale-middle", "3 puntos escala medio"),
    ("svg-spinners", "6-dots-rotate", "6 puntos rotar"),
    ("svg-spinners", "6-dots-scale", "6 puntos escala"),
    ("svg-spinners", "6-dots-scale-middle", "6 puntos escala medio"),
    ("svg-spinners", "8-dots-rotate", "8 puntos rotar"),
    # Rings (anillos)
    ("svg-spinners", "90-ring", "Anillo 90 grados"),
    ("svg-spinners", "90-ring-with-bg", "Anillo 90 grados con fondo"),
    ("svg-spinners", "180-ring", "Anillo 180 grados"),
    ("svg-spinners", "180-ring-with-bg", "Anillo 180 grados con fondo"),
    ("svg-spinners", "270-ring", "Anillo 270 grados"),
    ("svg-spinners", "270-ring-with-bg", "Anillo 270 grados con fondo"),
    ("svg-spinners", "ring-resize", "Anillo redimensionar"),
    # Bars (barras)
    ("svg-spinners", "bars-fade", "Barras desvanecer"),
    ("svg-spinners", "bars-rotate-fade", "Barras rotar desvanecer"),
    ("svg-spinners", "bars-scale", "Barras escala"),
    ("svg-spinners", "bars-scale-fade", "Barras escala desvanecer"),
    ("svg-spinners", "bars-scale-middle", "Barras escala medio"),
    # Blocks (bloques)
    ("svg-spinners", "blocks-scale", "Bloques escala"),
    ("svg-spinners", "blocks-shuffle-2", "Bloques barajar 2"),
    ("svg-spinners", "blocks-shuffle-3", "Bloques barajar 3"),
    ("svg-spinners", "blocks-wave", "Bloques onda"),
    # Otros
    ("svg-spinners", "bouncing-ball", "Pelota rebotando"),
    ("svg-spinners", "clock", "Reloj"),
    ("svg-spinners", "dot-revolve", "Punto revolucionar"),
    ("svg-spinners", "eclipse", "Eclipse"),
    ("svg-spinners", "eclipse-half", "Eclipse medio"),
    ("svg-spinners", "gooey-balls-1", "Bolas pegajosas 1"),
    ("svg-spinners", "gooey-balls-2", "Bolas pegajosas 2"),
    ("svg-spinners", "pulse", "Pulso"),
    ("svg-spinners", "pulse-2", "Pulso 2"),
    ("svg-spinners", "pulse-3", "Pulso 3"),
    ("svg-spinners", "pulse-multiple", "Pulso múltiple"),
    ("svg-spinners", "pulse-ring", "Anillo pulso"),
    ("svg-spinners", "pulse-rings-2", "Anillos pulso 2"),
    ("svg-spinners", "pulse-rings-3", "Anillos pulso 3"),
    ("svg-spinners", "pulse-rings-multiple", "Anillos pulso múltiple"),
    ("svg-spinners", "tadpole", "Renacuajo"),
    ("svg-spinners", "wifi", "WiFi"),
    ("svg-spinners", "wifi-fade", "WiFi desvanecer"),
    ("svg-spinners", "wind-toy", "Juguete viento"),
]

ICONIFY_API_BASE = "https://api.iconify.design"


def download_icon(
    collection: str, icon_name: str, output_dir: Path, description: Optional[str] = None
) -> bool:
    """
    Descargar un icono desde iconify API.

    Args:
        collection: Colección del icono (openmoji, ph, line-md, etc.)
        icon_name: Nombre del icono
        output_dir: Directorio donde guardar el icono
        description: Descripción opcional del icono

    Returns:
        True si se descargó correctamente, False en caso contrario
    """
    try:
        url = f"{ICONIFY_API_BASE}/{collection}:{icon_name}.svg"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            svg_content = response.text

            # Guardar archivo
            icon_path = output_dir / f"{icon_name}.svg"
            with open(icon_path, "w", encoding="utf-8") as f:
                f.write(svg_content)

            desc_text = f" ({description})" if description else ""
            print(f"[OK] Descargado: {collection}:{icon_name}.svg{desc_text}")
            return True
        else:
            print(f"[ERROR] Error {response.status_code}: {collection}:{icon_name}")
            return False

    except Exception as e:
        print(f"[ERROR] Error descargando {collection}:{icon_name}: {e}")
        return False


def main():
    """Descargar todos los iconos personalizados."""
    print("=" * 60)
    print("Descargando iconos personalizados")
    print("=" * 60)

    # Descargar iconos MDI
    print(f"\nDescargando iconos MDI (Material Design Icons)")
    print(f"Colección: https://yesicon.app/mdi")
    print(f"Total disponible: 7447 iconos")
    print(f"Descargando: {len(MDI_ICONS)} iconos seleccionados")
    print(f"Directorio: {CUSTOM_DIR}\n")

    mdi_downloaded = 0
    mdi_failed = 0
    mdi_skipped = 0

    for collection, icon_name, description in MDI_ICONS:
        icon_path = CUSTOM_DIR / f"{icon_name}.svg"

        # Saltar si ya existe
        if icon_path.exists():
            print(f"[SKIP] Ya existe: {icon_name}.svg")
            mdi_skipped += 1
            continue

        if download_icon(collection, icon_name, CUSTOM_DIR, description):
            mdi_downloaded += 1
        else:
            mdi_failed += 1

        # Pequeña pausa para no sobrecargar la API
        time.sleep(0.2)

    # Descargar iconos SVG Spinners
    print(f"\n{'=' * 60}")
    print(f"Descargando iconos SVG Spinners")
    print(f"Colección: https://yesicon.app/svg-spinners")
    print(f"Total disponible: 46 iconos")
    print(f"Descargando: {len(SVG_SPINNERS_ICONS)} iconos seleccionados")
    print(f"Directorio: {SVGSPINNER_DIR}\n")

    spinner_downloaded = 0
    spinner_failed = 0
    spinner_skipped = 0

    for collection, icon_name, description in SVG_SPINNERS_ICONS:
        icon_path = SVGSPINNER_DIR / f"{icon_name}.svg"

        # Saltar si ya existe
        if icon_path.exists():
            print(f"[SKIP] Ya existe: {icon_name}.svg")
            spinner_skipped += 1
            continue

        if download_icon(collection, icon_name, SVGSPINNER_DIR, description):
            spinner_downloaded += 1
        else:
            spinner_failed += 1

        # Pequeña pausa para no sobrecargar la API
        time.sleep(0.2)

    # Resumen final
    print(f"\n{'=' * 60}")
    print("RESUMEN FINAL")
    print(f"{'=' * 60}")
    print(f"\nIconos MDI:")
    print(f"  [OK] Descargados: {mdi_downloaded}")
    print(f"  [SKIP] Omitidos (ya existen): {mdi_skipped}")
    print(f"  [ERROR] Fallidos: {mdi_failed}")
    print(f"  Total procesados: {len(MDI_ICONS)}")
    print(f"\nIconos SVG Spinners:")
    print(f"  [OK] Descargados: {spinner_downloaded}")
    print(f"  [SKIP] Omitidos (ya existen): {spinner_skipped}")
    print(f"  [ERROR] Fallidos: {spinner_failed}")
    print(f"  Total procesados: {len(SVG_SPINNERS_ICONS)}")

    print(f"\n{'=' * 60}")


if __name__ == "__main__":
    main()
