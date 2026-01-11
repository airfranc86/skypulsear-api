import requests

BASE_URL = "http://localhost:8000"
API_KEY = "skypulse-wrf-smn-aws"  # API key válida configurada en el backend
TIMEOUT = 30

def test_weather_forecast_endpoint_returns_forecast_data():
    endpoint = f"{BASE_URL}/api/v1/weather/forecast"
    params = {
        "lat": -34.6037,   # Buenos Aires approx latitude
        "lon": -58.3816,   # Buenos Aires approx longitude
        "hours": 48
    }
    headers_valid = {
        "X-API-Key": API_KEY
    }
    headers_invalid = {
        "X-API-Key": "invalid_api_key"
    }

    # Test authorized request
    try:
        response = requests.get(endpoint, headers=headers_valid, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request to authorized weather forecast endpoint failed: {e}"
    
    assert response.status_code == 200, f"Expected status 200 for authorized request, got {response.status_code}"
    try:
        json_data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON for authorized request"
    assert isinstance(json_data, dict), "Response JSON is not an object for authorized request"
    # Basic sanity checks on response content for forecast data presence
    assert json_data, "Response JSON is empty for authorized request"

    # Test unauthorized request (no API key)
    try:
        response_unauth = requests.get(endpoint, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request to unauthorized weather forecast endpoint failed: {e}"
    assert response_unauth.status_code == 401, f"Expected status 401 for unauthorized request with no API key, got {response_unauth.status_code}"

    # Test unauthorized request (invalid API key)
    try:
        response_unauth_invalid = requests.get(endpoint, headers=headers_invalid, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request to unauthorized weather forecast endpoint with invalid key failed: {e}"
    assert response_unauth_invalid.status_code == 401, f"Expected status 401 for unauthorized request with invalid API key, got {response_unauth_invalid.status_code}"

test_weather_forecast_endpoint_returns_forecast_data()