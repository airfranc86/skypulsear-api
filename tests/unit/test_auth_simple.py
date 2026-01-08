"""
Simple authentication test to boost coverage.
"""

import pytest


def test_import_security_basic():
    """Test basic security imports work."""
    from app.utils.security import create_access_token, get_password_hash
    from app.utils.api_key_manager import api_key_manager

    # Test JWT creation (should not crash)
    token = create_access_token({"sub": "testuser"})
    assert token is not None
    assert isinstance(token, str)

    # Test password hashing (should not crash)
    test_password = "test123"  # Short password to avoid bcrypt 72-byte limit
    hashed = get_password_hash(test_password)
    assert hashed is not None
    assert hashed != test_password

    # Test API key manager (should not crash)
    api_key_manager.clear_cache()
    assert api_key_manager.get_key("test_provider") is None  # Unknown provider

    print("✅ Basic security imports working")


def test_import_auth_models_basic():
    """Test basic auth model creation."""
    from app.models.auth import UserCreate, UserProfile

    # Test user creation
    user = UserCreate(
        username="testuser", email="test@example.com", password="testpassword123"
    )
    assert user.username == "testuser"
    assert user.email == "test@example.com"

    # Test profile creation
    profile = UserProfile(user_type="general", location="Test Location")
    assert profile.user_type == "general"

    print("✅ Basic auth models working")


def test_backend_imports():
    """Test backend main imports without crashes."""
    from app.api.main import app

    assert app is not None
    assert app.title == "SkyPulse API"
    assert len(app.routes) > 0

    print("✅ Backend imports working")
