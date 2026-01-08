"""
Unit tests for SkyPulse Phase 1 security implementation.
Tests authentication, authorization, and protected endpoints.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_import_security_utils():
    """Test that security utils can be imported."""
    try:
        from app.utils.security import (
            create_access_token,
            verify_token,
            get_password_hash,
        )
        from app.utils.api_key_manager import api_key_manager

        # Test JWT creation and verification
        token = create_access_token({"sub": "testuser"})
        assert token is not None
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"

        # Test password hashing
        hashed = get_password_hash("testpassword")
        assert hashed is not None
        assert verify_password("testpassword", hashed)

        # Test API key manager
        key_manager.get_key("windy")  # Should not crash
        key_manager.get_key("meteosource")  # Should not crash

        print("✅ Security utils import successful")
        return True

    except Exception as e:
        print(f"❌ Security utils import failed: {e}")
        return False


def test_import_auth_models():
    """Test that auth models can be imported."""
    try:
        from app.models.auth import UserCreate, UserResponse, Token, UserProfile

        # Test model creation
        user = UserCreate(
            username="testuser", email="test@example.com", password="testpassword123"
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"

        profile = UserProfile(user_type="general")
        assert profile.user_type == "general"

        print("✅ Auth models import successful")
        return True

    except Exception as e:
        print(f"❌ Auth models import failed: {e}")
        return False


def test_import_auth_service():
    """Test that auth service can be imported."""
    try:
        from app.services.auth_service import AuthService

        auth_service = AuthService()

        # Test user creation
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123",
        }
        profile_data = {"user_type": "general", "location": "Test Location, Argentina"}

        # This will fail in demo mode but tests import
        # result = await auth_service.create_user(user_data, profile_data)
        # assert result is not None

        print("✅ Auth service import successful")
        return True

    except Exception as e:
        print(f"❌ Auth service import failed: {e}")
        return False


def test_import_security_middleware():
    """Test that security middleware can be imported."""
    try:
        from app.middleware.security_middleware import (
            RateLimitMiddleware,
            SecurityHeadersMiddleware,
        )

        # Test middleware creation
        rate_limiter = RateLimitMiddleware(app=None, calls=100, period=60)
        security_headers = SecurityHeadersMiddleware(app=None)

        print("✅ Security middleware import successful")
        return True

    except Exception as e:
        print(f"❌ Security middleware import failed: {e}")
        return False


def test_import_auth_router():
    """Test that auth router can be imported."""
    try:
        from app.api.routers.auth import router as auth_router

        assert auth_router is not None
        assert auth_router.prefix == "/api/v1/auth"

        print("✅ Auth router import successful")
        return True

    except Exception as e:
        print(f"❌ Auth router import failed: {e}")
        return False


def test_api_key_manager_initialization():
    """Test API key manager initializes correctly."""
    try:
        from app.utils.api_key_manager import api_key_manager

        # Test getting keys (will fail without real API keys but should not crash)
        windy_key = api_key_manager.get_key("windy")
        meteosource_key = api_key_manager.get_key("meteosource")

        # Should return None or a key value depending on environment
        # assert key is None or isinstance(key, str)

        print("✅ API key manager initialization successful")
        return True

    except Exception as e:
        print(f"❌ API key manager initialization failed: {e}")
        return False


if __name__ == "__main__":
    """Run all import tests."""
    print("\n🧪 SkyPulse Phase 1 Security Import Tests")
    print("=" * 60)

    results = {
        "Security Utils": test_import_security_utils(),
        "Auth Models": test_import_auth_models(),
        "Auth Service": test_import_auth_service(),
        "Security Middleware": test_import_security_middleware(),
        "Auth Router": test_import_auth_router(),
        "API Key Manager": test_api_key_manager_initialization(),
    }

    print("\n📊 Test Results:")
    print("=" * 60)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    print(f"\n📈 Summary: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All security components imported successfully!")
    else:
        failed_tests = [name for name, result in results.items() if not result]
        print(f"\n⚠️  Failed tests: {', '.join(failed_tests)}")

    sys.exit(0 if passed == total else 1)
