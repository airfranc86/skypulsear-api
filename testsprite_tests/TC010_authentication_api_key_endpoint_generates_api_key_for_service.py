import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_TC010_authentication_api_key_endpoint_generates_api_key_for_service():
    register_url = f"{BASE_URL}/api/v1/auth/register"
    login_url = f"{BASE_URL}/api/v1/auth/login"
    api_key_url = f"{BASE_URL}/api/v1/auth/api-key"

    # Generate unique user data to avoid conflicts
    unique_id = uuid.uuid4().hex
    username = f"testuser_tc010_{unique_id}"
    email = f"testuser_tc010_{unique_id}@example.com"
    password = "TestPass123!"

    # Register a new user
    try:
        resp_register = requests.post(
            register_url,
            json={"username": username, "email": email, "password": password},
            timeout=TIMEOUT
        )
        # Accept 201 Created or 400 if user already exists (to allow rerun)
        assert resp_register.status_code in (201, 400), f"Unexpected register status: {resp_register.status_code}"

        # Login to get bearer token
        resp_login = requests.post(
            login_url,
            json={"username": username, "password": password},
            timeout=TIMEOUT
        )
        assert resp_login.status_code == 200, f"Login failed with status {resp_login.status_code}"
        login_data = resp_login.json()
        access_token = login_data.get("access_token")
        token_type = login_data.get("token_type")
        assert access_token and token_type.lower() == "bearer", "Invalid access token or token type"

        headers = {"Authorization": f"Bearer {access_token}"}

        # Request API key for external service "windy"
        resp_api_key = requests.post(
            api_key_url,
            json={"service": "windy"},
            headers=headers,
            timeout=TIMEOUT
        )
        assert resp_api_key.status_code == 200, f"API key generation failed with status {resp_api_key.status_code}"
        api_key_data = resp_api_key.json()
        assert "api_key" in api_key_data and isinstance(api_key_data["api_key"], str) and api_key_data["api_key"], "API key missing or invalid in response"

    finally:
        # Cleanup: Delete the user if the API supports it.
        # The PRD does not specify user deletion endpoint; skip cleanup.
        pass

test_TC010_authentication_api_key_endpoint_generates_api_key_for_service()