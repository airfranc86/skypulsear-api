"""Utilidades centralizadas para retry logic con exponential backoff."""

import random
import time
from functools import wraps
from typing import Any, Callable, Optional, Type, Union

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    multiplier: float = 2.0,
    max_delay: float = 10.0,
    jitter: bool = True,
    retry_on: Optional[tuple[Type[Exception], ...]] = None,
) -> Callable:
    """
    Decorador para retry logic con exponential backoff y jitter.

    Args:
        max_attempts: Número máximo de intentos (incluyendo el primero)
        initial_delay: Delay inicial en segundos
        multiplier: Multiplicador para exponential backoff
        max_delay: Delay máximo en segundos
        jitter: Si True, agrega jitter aleatorio para evitar thundering herd
        retry_on: Tupla de excepciones que deben trigger retry (None = todas)

    Returns:
        Decorador que envuelve la función con retry logic

    Ejemplo:
        @retry_with_backoff(max_attempts=3, initial_delay=1.0, multiplier=2.0)
        def fetch_data():
            return requests.get(url)
    """
    if retry_on is None:
        retry_on = (Exception,)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        # Calcular delay con exponential backoff
                        delay = min(initial_delay * (multiplier**attempt), max_delay)

                        # Agregar jitter si está habilitado
                        if jitter:
                            jitter_amount = delay * 0.1 * random.random()
                            delay = delay + jitter_amount

                        logger.warning(
                            f"Intento {attempt + 1}/{max_attempts} falló, reintentando en {delay:.2f}s",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": max_attempts,
                                "delay": delay,
                                "error_type": type(e).__name__,
                                "error_message": str(e),
                            },
                        )

                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Todos los intentos fallaron después de {max_attempts} intentos",
                            extra={
                                "function": func.__name__,
                                "max_attempts": max_attempts,
                                "error_type": type(e).__name__,
                                "error_message": str(e),
                            },
                            exc_info=True,
                        )

            # Si llegamos aquí, todos los intentos fallaron
            if last_exception:
                raise last_exception

            raise RuntimeError(
                f"Función {func.__name__} falló después de {max_attempts} intentos"
            )

        return wrapper

    return decorator


def retry_async_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    multiplier: float = 2.0,
    max_delay: float = 10.0,
    jitter: bool = True,
    retry_on: Optional[tuple[Type[Exception], ...]] = None,
) -> Callable:
    """
    Decorador para retry logic asíncrono con exponential backoff y jitter.

    Args:
        max_attempts: Número máximo de intentos (incluyendo el primero)
        initial_delay: Delay inicial en segundos
        multiplier: Multiplicador para exponential backoff
        max_delay: Delay máximo en segundos
        jitter: Si True, agrega jitter aleatorio para evitar thundering herd
        retry_on: Tupla de excepciones que deben trigger retry (None = todas)

    Returns:
        Decorador que envuelve la función async con retry logic

    Ejemplo:
        @retry_async_with_backoff(max_attempts=3, initial_delay=1.0)
        async def fetch_data_async():
            return await httpx.get(url)
    """
    import asyncio

    if retry_on is None:
        retry_on = (Exception,)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        # Calcular delay con exponential backoff
                        delay = min(initial_delay * (multiplier**attempt), max_delay)

                        # Agregar jitter si está habilitado
                        if jitter:
                            jitter_amount = delay * 0.1 * random.random()
                            delay = delay + jitter_amount

                        logger.warning(
                            f"Intento {attempt + 1}/{max_attempts} falló, reintentando en {delay:.2f}s",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": max_attempts,
                                "delay": delay,
                                "error_type": type(e).__name__,
                                "error_message": str(e),
                            },
                        )

                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Todos los intentos fallaron después de {max_attempts} intentos",
                            extra={
                                "function": func.__name__,
                                "max_attempts": max_attempts,
                                "error_type": type(e).__name__,
                                "error_message": str(e),
                            },
                            exc_info=True,
                        )

            # Si llegamos aquí, todos los intentos fallaron
            if last_exception:
                raise last_exception

            raise RuntimeError(
                f"Función {func.__name__} falló después de {max_attempts} intentos"
            )

        return wrapper

    return decorator
