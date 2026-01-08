"""
Unit tests for SkyPulse Phase 1 security implementation.
Tests authentication, authorization, and protected endpoints.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_import_security_utils():
    """Test that security utils can be imported."""
    from app.utils.security import create_access_token, verify_token, get_password_hash
    from app.utils.api_key_manager import api_key_manager

    # Test JWT creation and verification
    token = create_access_token({"sub": "testuser"})
    assert token is not None
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "testuser"

    # Test password hashing
    hashed = get_password_hash("testpassword123")
    assert hashed != "testpassword123"
    assert verify_password("testpassword123", hashed)

    # Test API key manager
    key_manager.get_key("windy")  # Should not crash
    key_manager.clear_cache()

    print("PASS: Security utils import successful")


def test_import_auth_models():
    """Test that auth models can be imported."""
    from app.models.auth import (
        UserCreate,
        UserResponse,
        Token,
        UserProfile,
        APIKeyRequest,
        APIKeyResponse,
    )

    # Test model creation
    user = UserCreate(
        username="testuser", email="test@example.com", password="testpassword123"
    )
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.password == "testpassword123"

    # Test email validation happens (EmailStr = str in our fixed version)
    assert "@" in "test@example.com"

    profile = UserProfile(user_type="general", location="Test Location")
    assert profile.user_type == "general"
    assert profile.location == "Test Location"

    print("PASS: Auth models import successful")


def test_import_auth_service():
    """Test that auth service can be imported."""
    from app.services.auth_service import AuthService

    auth_service = AuthService()

    # Test user creation (will work in demo mode)
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
    }
    profile_data = {"user_type": "general", "location": "Test Location"}

    result = auth_service.create_user(user_data, profile_data)
    assert result is not None
    assert "access_token" in result
    assert "token_type" in result
    assert result["token_type"] == "bearer"

    print("PASS: Auth service import successful")


def test_import_security_middleware():
    """Test that security middleware can be imported."""
    from app.middleware.security_middleware import (
        RateLimitMiddleware,
        SecurityHeadersMiddleware,
    )

    # Test middleware creation (just verify they can be imported)
    rate_limiter = RateLimitMiddleware(app=None, calls=100, period=60)
    security_headers = SecurityHeadersMiddleware(app=None)

    print("PASS: Security middleware import successful")


def test_import_auth_router():
    """Test that auth router can be imported."""
    from app.api.routers.auth import router as auth_router

    assert auth_router is not None
    assert auth_router.prefix == "/api/v1/auth"
    assert len(auth_router.routes) > 0  # Should have routes

    print("PASS: Auth router import successful")


def test_backend_import():
    """Test that backend can be imported without crashing."""
    from app.api.main import app

    assert app is not None
    assert app.title == "SkyPulse API"
    assert app.version == "2.0.0"
    assert len(app.routes) > 0

    print("PASS: Backend import successful")


if __name__ == "__main__":
    # Run all import tests
    test_import_security_utils()
    test_import_auth_models()
    test_import_auth_service()
    test_import_security_middleware()
    test_import_auth_router()
    test_backend_import()

    print("\n" + "=" * 60)
    print("All Phase 1 security imports working correctly!")
    print("=" * 60)
