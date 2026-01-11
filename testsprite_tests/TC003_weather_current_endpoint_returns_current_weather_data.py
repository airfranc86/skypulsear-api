import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_weather_current_endpoint_returns_current_weather_data():
    valid_api_key = "skypulse-wrf-smn-aws"  # API key válida configurada en el backend
    invalid_api_key = "invalid_api_key_example"

    lat = -34.6037  # Buenos Aires approx latitude
    lon = -58.3816  # Buenos Aires approx longitude

    url = f"{BASE_URL}/api/v1/weather/current"

    # Test with valid API key
    headers_valid = {
        "X-API-Key": valid_api_key
    }
    params = {
        "lat": lat,
        "lon": lon
    }

    try:
        response = requests.get(url, headers=headers_valid, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request with valid API key failed: {e}"

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    try:
        data = response.json()
    except ValueError:
        assert False, "Response with valid API key is not valid JSON"

    # Basic validation: response should be a dict and contain at least one key
    assert isinstance(data, dict), "Response JSON is not an object"
    assert len(data) > 0, "Response JSON is empty"

    # Test with missing API key (unauthorized)
    try:
        response_no_key = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request without API key failed: {e}"
    assert response_no_key.status_code == 401, f"Expected 401 Unauthorized without API key, got {response_no_key.status_code}"

    # Test with invalid API key (unauthorized)
    headers_invalid = { "X-API-Key": invalid_api_key }
    try:
        response_invalid_key = requests.get(url, headers=headers_invalid, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request with invalid API key failed: {e}"
    assert response_invalid_key.status_code == 401, f"Expected 401 Unauthorized with invalid API key, got {response_invalid_key.status_code}"

test_weather_current_endpoint_returns_current_weather_data()
