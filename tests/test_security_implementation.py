"""
Security Tests

Basic tests to verify Phase 1 security implementation.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_health_endpoint_public():
    """Test that health endpoint is public."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_weather_endpoint_requires_auth():
    """Test that weather endpoints require authentication."""
    response = client.get("/api/v1/weather/current?lat=-34.6&lon=-58.4")
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]


def test_auth_registration():
    """Test user registration endpoint."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "user_data": {
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpassword123",
            },
            "profile_data": {
                "user_type": "general",
                "location": "Buenos Aires, Argentina",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_auth_login():
    """Test user login endpoint."""
    # First register a user
    client.post(
        "/api/v1/auth/register",
        json={
            "user_data": {
                "username": "loginuser",
                "email": "login@example.com",
                "password": "loginpassword123",
            },
            "profile_data": {"user_type": "general"},
        },
    )

    # Then login
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "loginuser", "password": "loginpassword123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "loginuser"


def test_protected_weather_with_auth():
    """Test weather endpoint with valid authentication."""
    # Register and login to get token
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "user_data": {
                "username": "weatheruser",
                "email": "weather@example.com",
                "password": "weatherpassword123",
            },
            "profile_data": {"user_type": "agriculture"},
        },
    )

    token = register_response.json()["access_token"]

    # Access weather endpoint
    response = client.get(
        "/api/v1/weather/current?lat=-34.6&lon=-58.4",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "location" in data
    assert "current" in data
    assert data["user_context"]["authenticated"] == True


def test_invalid_token_rejected():
    """Test that invalid tokens are rejected."""
    response = client.get(
        "/api/v1/weather/current?lat=-34.6&lon=-58.4",
        headers={"Authorization": "Bearer invalid_token_12345"},
    )

    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]


def test_security_headers_present():
    """Test that security headers are present."""
    response = client.get("/health")
    headers = response.headers

    # Check for security headers
    assert "X-Content-Type-Options" in headers
    assert headers["X-Content-Type-Options"] == "nosniff"

    assert "X-Frame-Options" in headers
    assert headers["X-Frame-Options"] == "DENY"


if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v"])
