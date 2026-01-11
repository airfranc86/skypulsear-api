"""
API Key Management System

Manages API keys from various providers with caching and security features.
"""

import os
import logging
from typing import Dict, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class APIKeyProvider(ABC):
    """Abstract base class for API key providers."""

    @abstractmethod
    def get_key(self, service: str) -> Optional[str]:
        """Get API key for a service."""
        pass


class EnvironmentKeyProvider(APIKeyProvider):
    """Environment variable based API key provider."""

    def get_key(self, service: str) -> Optional[str]:
        """Get API key from environment variables."""
        key = os.getenv(f"{service.upper()}_API_KEY")
        if not key:
            logger.error(f"No API key found in environment for service: {service}")
        return key


class APIKeyManager:
    """Manages API keys from various providers."""

    def __init__(self, provider: APIKeyProvider = None):
        self.provider = provider or EnvironmentKeyProvider()
        self._key_cache: Dict[str, str] = {}

    def get_key(self, service: str) -> Optional[str]:
        """Get API key for a service with caching."""
        if service not in self._key_cache:
            key = self.provider.get_key(service)
            if key:
                self._key_cache[service] = key
                logger.info(f"API key loaded for service: {service}")
        return self._key_cache.get(service)

    def clear_cache(self, service: Optional[str] = None):
        """Clear cached API keys."""
        if service:
            self._key_cache.pop(service, None)
            logger.info(f"Cleared API key cache for service: {service}")
        else:
            self._key_cache.clear()
            logger.info("Cleared all API key cache")


# Global instance
api_key_manager = APIKeyManager()
