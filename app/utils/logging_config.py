"""Configuración de logging para SkyPulse."""

import logging
import os
from typing import Optional


def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """
    Configurar sistema de logging.
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Si es None, usa LOG_LEVEL de variables de entorno o INFO por defecto.
    
    Returns:
        Logger configurado
    """
    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configurado con nivel: {log_level}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Obtener logger para un módulo específico.
    
    Args:
        name: Nombre del módulo (típicamente __name__)
    
    Returns:
        Logger configurado para el módulo
    """
    return logging.getLogger(name)

