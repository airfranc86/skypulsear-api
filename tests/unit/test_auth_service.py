"""
Unit tests for SkyPulse authentication system.
Tests authentication, JWT tokens, and password validation.
"""

import pytest
from datetime import datetime, UTC, timedelta


class TestPasswordValidation:
    """Test password hashing and validation."""

    def test_password_hashing():
        """Test that password hashing works correctly."""
        from app.utils.security import get_password_hash, verify_password

        password = "test_password123"

        hashed = get_password_hash(password)
        assert hashed is not None
        assert hashed != password
        assert len(hashed) >= 60  # bcrypt hashes are at least 60 characters

        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False
        assert verify_password("Test123", "different_hash") is False


class TestJWTTokens:
    """Test JWT token creation and validation."""

    def test_token_creation():
        """Test that JWT tokens can be created."""
        from app.utils.security import create_access_token, verify_token

        # Test creating token
        token = create_access_token({"sub": "testuser"})
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically longer

        # Test token verification
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert isinstance(payload.get("exp"), (int, float))
        assert "exp" in payload
        assert payload["exp"] > datetime.now(UTC)

        # Test expired token
        old_token = create_access_token({"sub": "olduser", "exp": 0})
        assert old_token is not None
        assert verify_token(old_token) is None  # Expired tokens return None


class TestAPIKeyManagement:
    """Test API key management system."""

    def test_api_key_caching():
        """Test that API keys are cached properly."""
        from app.utils.api_key_manager import api_key_manager

        # Clear cache
        api_key_manager.clear_cache()

        # Get first key (should cache it)
        key1 = api_key_manager.get_key("windy")
        key1_again = api_key_manager.get_key("windy")

        assert key1 == key1_again  # Should be cached
        assert key1 is not None or isinstance(key1, str)

        # Test second key (should also be cached)
        key2 = api_key_manager.get_key("meteosource")
        assert isinstance(key2, (str, type(None)))

        # Test clearing specific key
        api_key_manager.clear_cache("windy")
        key_after_clear = api_key_manager.get_key("windy")
        assert key_after_clear != key1  # Cache was cleared


class TestSecurityFeatures:
    """Test security utility functions."""

    def test_mask_api_key():
        """Test API key masking for logging."""
        from app.utils.security import mask_api_key

        key = "sk_test_secret_key_xyz123456"
        masked = mask_api_key(key)

        assert key not in masked
        assert masked.startswith(key[:4])  # Keep first 4 chars
        assert len(masked) <= len(key) + 8  # Only add 4-8 asterisks
        assert masked.endswith(key[-4:])  # Keep last 4 chars
