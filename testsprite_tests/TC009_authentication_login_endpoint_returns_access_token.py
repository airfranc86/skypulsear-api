import requests
import uuid

BASE_URL = "http://localhost:8000"
REGISTER_ENDPOINT = "/api/v1/auth/register"
LOGIN_ENDPOINT = "/api/v1/auth/login"
TIMEOUT = 30

def test_TC009_authentication_login_endpoint_returns_access_token():
    # Generate unique user data for registration
    unique_id = uuid.uuid4().hex
    username = f"testuser_{unique_id}"
    email = f"test_{unique_id}@example.com"
    password = "TestPassword123!"
    
    register_url = BASE_URL + REGISTER_ENDPOINT
    login_url = BASE_URL + LOGIN_ENDPOINT
    headers = {"Content-Type": "application/json"}
    
    try:
        # First, register a new user
        register_response = requests.post(
            register_url,
            json={"username": username, "email": email, "password": password},
            headers=headers,
            timeout=TIMEOUT
        )
        # Accept 201 Created or 400 if user already exists (to allow rerun)
        assert register_response.status_code in (201, 400), f"Registration failed with status {register_response.status_code}"
        
        # Define valid credentials (the user we just created)
        valid_credentials = {
            "username": username,
            "password": password
        }
        # Define invalid credentials
        invalid_credentials = {
            "username": "invaliduser",
            "password": "WrongPassword!"
        }
        
        # Test valid login
        response_valid = requests.post(login_url, json=valid_credentials, headers=headers, timeout=TIMEOUT)
        assert response_valid.status_code == 200, f"Expected 200 for valid login, got {response_valid.status_code}"
        json_valid = response_valid.json()
        assert "access_token" in json_valid, "access_token missing in valid login response"
        assert isinstance(json_valid["access_token"], str) and len(json_valid["access_token"]) > 0, "access_token is not valid"
        assert "token_type" in json_valid, "token_type missing in valid login response"
        assert json_valid["token_type"].lower() == "bearer", f"token_type expected to be 'bearer', got {json_valid['token_type']}"
        
        # Test invalid login
        response_invalid = requests.post(login_url, json=invalid_credentials, headers=headers, timeout=TIMEOUT)
        assert response_invalid.status_code == 401, f"Expected 401 for invalid login, got {response_invalid.status_code}"
        
    except requests.RequestException as e:
        assert False, f"HTTP request failed: {e}"
    except ValueError as e:
        assert False, f"Failed to parse JSON response: {e}"

test_TC009_authentication_login_endpoint_returns_access_token()