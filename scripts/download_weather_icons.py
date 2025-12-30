"""
Script para descargar iconos de Weather Icons desde yesicon.app/iconify.

Weather Icons tiene 219 iconos disponibles. Este script descarga los más relevantes
para un sistema meteorológico.
"""

import requests
from pathlib import Path
import time
from typing import List, Tuple

BASE_DIR = Path(__file__).parent.parent
ICONS_DIR = BASE_DIR / "static" / "icons" / "yesicon" / "wi"
ICONS_DIR.mkdir(parents=True, exist_ok=True)

# Iconos más relevantes para sistema meteorológico
WEATHER_ICONS: List[Tuple[str, str]] = [
    # Condiciones básicas
    ("cloud", "Nube básica"),
    ("cloudy", "Nublado"),
    ("cloudy-gusts", "Nublado con ráfagas"),
    ("cloudy-windy", "Nublado con viento"),
    ("day-cloudy", "Día nublado"),
    ("day-sunny", "Día soleado"),
    ("day-sunny-overcast", "Día soleado con nubes"),
    
    # Precipitación
    ("rain", "Lluvia"),
    ("day-rain", "Día lluvioso"),
    ("day-rain-mix", "Día lluvia mixta"),
    ("day-rain-wind", "Día lluvia con viento"),
    ("day-showers", "Día chubascos"),
    ("day-sprinkle", "Día llovizna"),
    
    # Nieve
    ("snow", "Nieve"),
    ("day-snow", "Día nevado"),
    ("day-snow-wind", "Día nieve con viento"),
    ("day-sleet", "Día aguanieve"),
    ("day-sleet-storm", "Día tormenta de aguanieve"),
    
    # Tormentas
    ("thunderstorm", "Tormenta"),
    ("day-thunderstorm", "Día tormenta"),
    ("day-storm-showers", "Día chubascos tormentosos"),
    ("day-snow-thunderstorm", "Día tormenta de nieve"),
    ("lightning", "Rayo"),
    
    # Viento
    ("windy", "Ventoso"),
    ("day-windy", "Día ventoso"),
    ("day-light-wind", "Día viento ligero"),
    ("strong-wind", "Viento fuerte"),
    
    # Niebla y visibilidad
    ("fog", "Niebla"),
    ("day-fog", "Día con niebla"),
    ("day-haze", "Día con bruma"),
    
    # Temperatura
    ("thermometer", "Termómetro"),
    ("thermometer-exterior", "Termómetro exterior"),
    ("thermometer-internal", "Termómetro interno"),
    ("hot", "Calor"),
    ("cold", "Frío"),
    
    # Direcciones
    ("direction-up", "Norte"),
    ("direction-down", "Sur"),
    ("direction-left", "Oeste"),
    ("direction-right", "Este"),
    ("direction-up-right", "Noreste"),
    ("direction-up-left", "Noroeste"),
    ("direction-down-right", "Sureste"),
    ("direction-down-left", "Suroeste"),
    
    # Otros
    ("barometer", "Barómetro"),
    ("humidity", "Humedad"),
    ("degrees", "Grados"),
    ("celsius", "Celsius"),
    ("fahrenheit", "Fahrenheit"),
    ("sunrise", "Amanecer"),
    ("sunset", "Atardecer"),
    ("moon-new", "Luna nueva"),
    ("moon-full", "Luna llena"),
    ("horizon", "Horizonte"),
]

ICONIFY_API_BASE = "https://api.iconify.design/wi"


def download_icon(icon_name: str) -> bool:
    """
    Descargar un icono desde iconify API.
    
    Args:
        icon_name: Nombre del icono
        
    Returns:
        True si se descargó correctamente, False en caso contrario
    """
    try:
        url = f"{ICONIFY_API_BASE}/{icon_name}.svg"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            svg_content = response.text
            
            # Asegurar que tenga los atributos necesarios
            if 'width="22"' not in svg_content and 'width=' not in svg_content:
                # Agregar atributos si no los tiene
                svg_content = svg_content.replace(
                    '<svg',
                    '<svg width="22" height="22" fill="currentColor"'
                )
            
            # Guardar archivo
            icon_path = ICONS_DIR / f"{icon_name}.svg"
            with open(icon_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
            
            print(f"[OK] Descargado: {icon_name}.svg")
            return True
        else:
            print(f"[ERROR] Error {response.status_code}: {icon_name}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error descargando {icon_name}: {e}")
        return False


def main():
    """Descargar todos los iconos de Weather Icons."""
    print(f"Descargando iconos de Weather Icons a: {ICONS_DIR}")
    print(f"Total de iconos a descargar: {len(WEATHER_ICONS)}\n")
    
    downloaded = 0
    failed = 0
    
    for icon_name, description in WEATHER_ICONS:
        if download_icon(icon_name):
            downloaded += 1
        else:
            failed += 1
        
        # Pequeña pausa para no sobrecargar la API
        time.sleep(0.2)
    
    print(f"\n{'='*50}")
    print(f"[OK] Descargados: {downloaded}")
    print(f"[ERROR] Fallidos: {failed}")
    print(f"Total: {len(WEATHER_ICONS)}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

