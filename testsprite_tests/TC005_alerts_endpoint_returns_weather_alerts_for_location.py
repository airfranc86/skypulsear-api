import requests

BASE_URL = "http://localhost:8000"
API_KEY = "skypulse-wrf-smn-aws"  # API key válida configurada en el backend

def test_alerts_endpoint_returns_weather_alerts_for_location():
    # Define valid coordinates for testing
    lat = -34.6037
    lon = -58.3816
    hours = 24  # Optional parameter

    headers_auth = {
        "X-API-Key": API_KEY
    }

    # 1. Test successful request with valid API key and all parameters
    params = {
        "lat": lat,
        "lon": lon,
        "hours": hours
    }
    try:
        response = requests.get(f"{BASE_URL}/api/v1/alerts", headers=headers_auth, params=params, timeout=30)
        # Aceptar tanto 200 como 503 como válidos (503 cuando servicios externos no están disponibles)
        assert response.status_code in (200, 503), f"Expected 200 or 503 but got {response.status_code}"
        data = response.json()
        assert isinstance(data, dict), "Response is not a JSON object"
        
        if response.status_code == 200:
            # Si servicios están disponibles, validar estructura completa
            assert "location" in data, "Missing 'location' in response"
            assert "alerts" in data, "Missing 'alerts' in response"
            assert "alert_count" in data, "Missing 'alert_count' in response"
            assert "max_level" in data, "Missing 'max_level' in response"
            assert "max_level_name" in data, "Missing 'max_level_name' in response"
            assert isinstance(data["alerts"], list), "'alerts' should be a list"
            assert isinstance(data["alert_count"], int), "'alert_count' should be an integer"
        elif response.status_code == 503:
            # Si servicios no están disponibles, validar mensaje de error
            # La respuesta 503 tiene estructura: {"error": {"code": "...", "message": "...", "correlation_id": "..."}}
            assert "error" in data, "503 response missing 'error' field"
            assert "message" in data["error"], "503 response missing 'error.message' field"
            error_message = data["error"]["message"]
            assert "No se pudieron obtener datos meteorológicos" in error_message or "Servicio temporalmente no disponible" in error_message, f"Unexpected error message: {error_message}"
    except requests.RequestException as e:
        assert False, f"RequestException occurred during valid request: {e}"

    # 2. Test successful request without hours parameter (rely on default)
    params = {
        "lat": lat,
        "lon": lon
    }
    try:
        response = requests.get(f"{BASE_URL}/api/v1/alerts", headers=headers_auth, params=params, timeout=30)
        # Aceptar tanto 200 como 503 como válidos
        assert response.status_code in (200, 503), f"Expected 200 or 503 but got {response.status_code}"
        data = response.json()
        if response.status_code == 200:
            assert "alerts" in data
    except requests.RequestException as e:
        assert False, f"RequestException occurred during request without hours: {e}"

    # 3. Test unauthorized request (no API key)
    params = {
        "lat": lat,
        "lon": lon,
        "hours": hours
    }
    try:
        response = requests.get(f"{BASE_URL}/api/v1/alerts", params=params, timeout=30)
        assert response.status_code == 401, f"Expected 401 Unauthorized without API key, got {response.status_code}"
    except requests.RequestException as e:
        assert False, f"RequestException occurred during unauthorized request: {e}"

test_alerts_endpoint_returns_weather_alerts_for_location()
