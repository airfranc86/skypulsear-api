"""Tests para retry logic."""

import pytest
import time
from unittest.mock import patch, MagicMock

from app.utils.retry import retry_with_backoff, retry_async_with_backoff


def test_retry_success_on_first_attempt():
    """Test que una función exitosa no hace retry."""
    call_count = 0

    @retry_with_backoff(max_attempts=3)
    def success_func():
        nonlocal call_count
        call_count += 1
        return "success"

    result = success_func()
    assert result == "success"
    assert call_count == 1


def test_retry_success_after_failures():
    """Test que retry funciona después de fallos."""
    call_count = 0

    @retry_with_backoff(max_attempts=3, initial_delay=0.1)
    def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("Temporary failure")
        return "success"

    result = flaky_func()
    assert result == "success"
    assert call_count == 2


def test_retry_exhausts_attempts():
    """Test que retry lanza excepción después de agotar intentos."""
    call_count = 0

    @retry_with_backoff(max_attempts=3, initial_delay=0.1)
    def always_failing_func():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Always fails")

    with pytest.raises(ConnectionError):
        always_failing_func()

    assert call_count == 3


def test_retry_only_on_specified_exceptions():
    """Test que retry solo reintenta excepciones especificadas."""
    call_count = 0

    @retry_with_backoff(max_attempts=3, retry_on=(ConnectionError,))
    def func_with_different_error():
        nonlocal call_count
        call_count += 1
        raise ValueError("Different error")

    with pytest.raises(ValueError):
        func_with_different_error()

    # No debería hacer retry para ValueError
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_async_success():
    """Test que retry async funciona correctamente."""
    call_count = 0

    @retry_async_with_backoff(max_attempts=3, initial_delay=0.1)
    async def async_success_func():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await async_success_func()
    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_async_with_failures():
    """Test que retry async reintenta después de fallos."""
    call_count = 0

    @retry_async_with_backoff(max_attempts=3, initial_delay=0.1)
    async def async_flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("Temporary failure")
        return "success"

    result = await async_flaky_func()
    assert result == "success"
    assert call_count == 2
