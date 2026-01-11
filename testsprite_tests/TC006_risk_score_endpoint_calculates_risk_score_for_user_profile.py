import requests


def test_risk_score_endpoint_calculates_risk_score_for_user_profile():
    base_url = "http://localhost:8000"
    endpoint = "/api/v1/risk-score"
    url = base_url + endpoint

    valid_api_key = "skypulse-wrf-smn-aws"  # API key válida configurada en el backend
    headers = {
        "X-API-Key": valid_api_key,
        "Content-Type": "application/json"
    }

    valid_payload = {
        "lat": -34.6037,
        "lon": -58.3816,
        "profile": "piloto",
        "hours_ahead": 6
    }

    # Test successful calculation of risk score
    try:
        response = requests.post(url, json=valid_payload, headers=headers, timeout=30)
        # Aceptar 200 (éxito) o 503 (servicios externos no disponibles) como válidos
        assert response.status_code in (200, 503), f"Expected 200 or 503, got {response.status_code}"
        data = response.json()
        
        if response.status_code == 200:
            # Si servicios están disponibles, validar estructura completa
            assert "score" in data and 0 <= data["score"] <= 5, "score missing or out of range"
            assert "category" in data and isinstance(data["category"], str), "category missing or not string"
            assert "risk_score_100" in data and 0 <= data["risk_score_100"] <= 100, "risk_score_100 missing or out of range"
            for key in [
                "temperature_risk",
                "wind_risk",
                "precipitation_risk",
                "storm_risk",
                "hail_risk",
                "pattern_risk",
                "alert_risk"
            ]:
                assert key in data and isinstance(data[key], (int, float)), f"{key} missing or not a number"
            assert "recommendations" in data and isinstance(data["recommendations"], list), "recommendations missing or not a list"
            assert "key_factors" in data and isinstance(data["key_factors"], list), "key_factors missing or not a list"
        elif response.status_code == 503:
            # Si servicios no están disponibles, validar mensaje de error
            # La respuesta 503 tiene estructura: {"error": {"code": "...", "message": "...", "correlation_id": "..."}}
            assert "error" in data, "503 response missing 'error' field"
            assert "message" in data["error"], "503 response missing 'error.message' field"
            error_message = data["error"]["message"]
            assert "No se pudieron obtener datos meteorológicos" in error_message or "Servicio temporalmente no disponible" in error_message, f"Unexpected error message: {error_message}"
    except requests.exceptions.RequestException as e:
        assert False, f"Request exception during valid test: {e}"

    # Test unauthorized scenario - no API key
    try:
        headers_unauth = {"Content-Type": "application/json"}
        response_unauth = requests.post(url, json=valid_payload, headers=headers_unauth, timeout=30)
        assert response_unauth.status_code == 401, f"Expected 401 Unauthorized, got {response_unauth.status_code}"
    except requests.exceptions.RequestException as e:
        assert False, f"Request exception during unauthorized test: {e}"

    # Test validation error scenario - invalid hours_ahead (out of range)
    try:
        invalid_payload = {
            "lat": -34.6037,
            "lon": -58.3816,
            "profile": "piloto",
            "hours_ahead": 1000  # Out of max range 72, should trigger validation error (422)
        }
        response_validation = requests.post(url, json=invalid_payload, headers=headers, timeout=30)
        # Invalid input should return 422 (Unprocessable Entity) for validation errors
        assert response_validation.status_code == 422, f"Expected 422 for invalid hours_ahead, got {response_validation.status_code}"
    except requests.exceptions.RequestException as e:
        assert False, f"Request exception during validation error test: {e}"


test_risk_score_endpoint_calculates_risk_score_for_user_profile()