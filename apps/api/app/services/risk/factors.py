"""
Risk Factors Module

Individual risk factor calculations for temperature, wind, precipitation, and storms.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class RiskFactors:
    """Individual risk factor calculations (0-100 scale)."""

    @staticmethod
    def calculate_temperature_risk(
        weather_data: Dict[str, Any], profile_config: Dict[str, Any]
    ) -> float:
        """
        Calculate temperature risk factor (0-100).

        Risk increases exponentially outside optimal range (15-25°C).
        """
        temp = weather_data.get("temperature", 20.0)
        sensitivity = profile_config.get("temperature_sensitivity", 50) / 100.0

        # Calculate distance from optimal range
        optimal_min, optimal_max = 15.0, 25.0

        if optimal_min <= temp <= optimal_max:
            return 0.0  # Within optimal range

        if temp < optimal_min:
            distance = (optimal_min - temp) / (optimal_min - 5.0)
        else:
            distance = (temp - optimal_max) / (45.0 - optimal_max)

        # Cap at 100
        base_risk = min(distance * 100.0, 100.0)
        return base_risk * sensitivity

    @staticmethod
    def calculate_wind_risk(
        weather_data: Dict[str, Any], profile_config: Dict[str, Any]
    ) -> float:
        """
        Calculate wind risk factor (0-100).

        Risk increases exponentially with wind speed.
        """
        wind_speed = weather_data.get("wind_speed", 0.0)
        sensitivity = profile_config.get("wind_sensitivity", 50) / 100.0

        # Define wind thresholds (km/h)
        CALM = 10.0
        LIGHT_BREEZE = 20.0
        MODERATE_WIND = 30.0
        STRONG_WIND = 40.0
        GALE_FORCE = 50.0

        if wind_speed <= CALM:
            base_risk = 0.0
        elif wind_speed <= LIGHT_BREEZE:
            base_risk = (wind_speed - CALM) / 10.0 * 20.0
        elif wind_speed <= MODERATE_WIND:
            base_risk = ((wind_speed - LIGHT_BREEZE) / 10.0 * 0.5) + 20.0
        elif wind_speed <= STRONG_WIND:
            base_risk = ((wind_speed - MODERATE_WIND) / 10.0 * 0.7) + 40.0
        else:
            base_risk = ((wind_speed - STRONG_WIND) / 10.0 * 1.0) + 60.0

        # Apply sensitivity and cap at 100
        risk = min(base_risk * sensitivity, 100.0)
        return max(risk, 0.0)

    @staticmethod
    def calculate_precipitation_risk(
        weather_data: Dict[str, Any], profile_config: Dict[str, Any]
    ) -> float:
        """
        Calculate precipitation risk factor (0-100).

        Risk increases linearly with precipitation amount.
        """
        precip = weather_data.get("precipitation", 0.0)
        sensitivity = profile_config.get("precipitation_sensitivity", 50) / 100.0

        # Risk is proportional to precipitation amount
        risk = min(precip * sensitivity, 100.0)
        return max(risk, 0.0)

    @staticmethod
    def calculate_storm_risk(
        weather_data: Dict[str, Any], profile_config: Dict[str, Any]
    ) -> float:
        """
        Calculate storm risk factor (0-100).

        Uses storm_risk from normalized weather (0-1 scale).
        """
        storm_risk = weather_data.get("storm_risk", 0.0)
        sensitivity = profile_config.get("storm_sensitivity", 50) / 100.0

        # Apply sensitivity and scale to 0-100
        risk = storm_risk * sensitivity * 100.0
        return min(risk, 100.0)

    @staticmethod
    def calculate_pattern_risk(
        weather_data: Dict[str, Any], profile_config: Dict[str, Any]
    ) -> float:
        """
        Calculate pattern risk factor (0-100).

        Based on detected weather patterns with severity (1-5).
        """
        patterns = weather_data.get("patterns", [])
        if not patterns:
            return 0.0

        sensitivity = profile_config.get("pattern_sensitivity", 50) / 100.0

        # Calculate max pattern severity
        max_severity = max((p.get("severity", 1) for p in patterns), default=1)

        # Map severity (1-5) to risk (0-100)
        # 1=minor, 2=moderate, 3=significant, 4=severe, 5=extreme
        base_risk = ((max_severity - 1) / 4) * 100.0

        # Apply sensitivity
        risk = base_risk * sensitivity
        return min(risk, 100.0)

    @staticmethod
    def calculate_all_factors(
        weather_data: Dict[str, Any], profile_config: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate all individual risk factors.

        Returns dictionary of factor names to scores (0-100).
        """
        factors = {}

        factors["temperature"] = RiskFactors.calculate_temperature_risk(
            weather_data, profile_config
        )
        factors["wind"] = RiskFactors.calculate_wind_risk(weather_data, profile_config)
        factors["precipitation"] = RiskFactors.calculate_precipitation_risk(
            weather_data, profile_config
        )
        factors["storm"] = RiskFactors.calculate_storm_risk(
            weather_data, profile_config
        )
        factors["pattern"] = RiskFactors.calculate_pattern_risk(
            weather_data, profile_config
        )

        logger.debug(f"Calculated risk factors: {factors}")
        return factors
