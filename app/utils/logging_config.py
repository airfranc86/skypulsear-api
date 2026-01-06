"""Configuración de logging estructurado JSON para SkyPulse."""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Importar función para obtener correlation ID
try:
    from app.api.middleware.correlation_id import get_correlation_id
except ImportError:
    # Fallback si no está disponible (durante imports iniciales)
    def get_correlation_id() -> str:
        return ""


class JSONFormatter(logging.Formatter):
    """Formatter que produce logs en formato JSON estructurado."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Formatear log record como JSON estructurado.

        Args:
            record: LogRecord a formatear

        Returns:
            String JSON con el log estructurado
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Agregar correlation ID del contexto si está disponible
        correlation_id = get_correlation_id()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Agregar correlation_id del record si existe (para compatibilidad)
        if hasattr(record, "correlation_id") and record.correlation_id:
            log_data["correlation_id"] = record.correlation_id

        # Agregar campos extra del record
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "correlation_id",
            ):
                log_data[key] = value

        # Agregar información de excepción si existe
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """
    Configurar sistema de logging estructurado JSON.

    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Si es None, usa LOG_LEVEL de variables de entorno o INFO por defecto.

    Returns:
        Logger configurado
    """
    log_level = level or os.getenv("LOG_LEVEL", "INFO")

    # Limpiar handlers existentes para evitar duplicados
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Configurar handler con formatter JSON
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    # Configurar logger raíz
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(handler)

    logger = logging.getLogger(__name__)
    logger.info(
        "Logging estructurado JSON configurado",
        extra={"log_level": log_level},
    )

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
