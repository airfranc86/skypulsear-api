"""
Risk Calculator Module

Core risk calculation logic for SkyPulse.
Handles combining weather data with risk factors to calculate final scores.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, UTC, timedelta

from app.data.schemas.normalized_weather import UnifiedForecast
from app.services.risk.profiles import (
    ProfileConfigurations,
    RiskProfileConfig,
    WeatherConditionThresholds,
    RiskCategory,
)
from app.services.alert_service import AlertLevel

logger = logging.getLogger(__name__)


class RiskCalculator:
    """Core risk calculation engine for SkyPulse."""

    def __init__(self, profile_config: RiskProfileConfig):
        """Initialize risk calculator with profile configuration."""
        self.profile = profile_config

    def calculate_risk_score(
        self, weather_data: UnifiedForecast, detected_patterns: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive risk score for given weather data.

        Args:
            weather_data: Normalized weather forecast
            detected_patterns: List of detected weather patterns

        Returns:
            Dictionary with complete risk assessment
        """
        logger.info(f"Calculating risk for profile: {self.profile.profile_name}")

        # Step 1: Calculate individual factor risks (0-100)
        factor_scores = self._calculate_factor_scores(weather_data)

        # Step 2: Apply profile sensitivities (0-100)
        weighted_scores = self._apply_profile_sensitivities(factor_scores)

        # Step 3: Calculate overall score (0-5)
        overall_score = self._calculate_overall_score(weighted_scores)

        # Step 4: Determine risk category and alert level
        risk_category = self._determine_risk_category(overall_score)
        alert_level = self._determine_alert_level(overall_score, detected_patterns)

        # Step 5: Generate operational recommendations
        recommendations = self._generate_recommendations(
            overall_score, risk_category, factor_scores
        )

        return {
            "overall_score": overall_score,
            "risk_level": risk_category,
            "alert_level": alert_level,
            "factor_scores": factor_scores,
            "weighted_scores": weighted_scores,
            "recommendations": recommendations,
            "profile": self.profile.profile_name,
            "profile_config": self.profile.model_dump(),
            "calculated_at": datetime.now(UTC),
        }

    def _calculate_factor_scores(
        self, weather_data: UnifiedForecast
    ) -> Dict[str, float]:
        """Calculate individual risk factors (0-100 scale)."""

        scores = {}

        # Temperature risk
        scores["temperature"] = self._calculate_temperature_risk(weather_data)

        # Wind risk
        scores["wind"] = self._calculate_wind_risk(weather_data)

        # Precipitation risk
        scores["precipitation"] = self._calculate_precipitation_risk(weather_data)

        # Storm risk
        scores["storm"] = self._calculate_storm_risk(weather_data)

        # Pattern risk (if patterns detected)
        if weather_data.patterns:
            scores["pattern"] = self._calculate_pattern_risk(weather_data.patterns)
        else:
            scores["pattern"] = 0.0

        logger.debug(f"Factor scores: {scores}")
        return scores

    def _calculate_temperature_risk(self, weather_data: UnifiedForecast) -> float:
        """Calculate temperature-related risk (0-100)."""
        temp = weather_data.current.get("temperature", 20.0)

        # Use profile's temperature sensitivity
        sensitivity = self.profile.temperature_sensitivity / 100.0  # Convert to 0-1

        # Calculate distance from comfortable range (15-25°C is optimal)
        optimal_min, optimal_max = 15.0, 25.0

        if optimal_min <= temp <= optimal_max:
            # Within optimal range - no risk
            base_risk = 0.0
        else:
            # Outside optimal range - calculate how far off
            if temp < optimal_min:
                distance = (optimal_min - temp) / (
                    optimal_min - 5.0
                )  # Very cold is -5°C
            else:
                distance = (temp - optimal_max) / (
                    40.0 - optimal_max
                )  # Very hot is 40°C

            base_risk = min(distance * 100, 100.0)  # Cap at 100

        return base_risk * sensitivity

    def _calculate_wind_risk(self, weather_data: UnifiedForecast) -> float:
        """Calculate wind-related risk (0-100)."""
        wind_speed = weather_data.current.get("wind_speed", 0.0)

        # Use profile's wind sensitivity
        sensitivity = self.profile.wind_sensitivity / 100.0

        # Risk increases exponentially with wind speed
        if wind_speed < WeatherConditionThresholds.CALM:
            base_risk = 0.0
        elif wind_speed < WeatherConditionThresholds.LIGHT_BREEZE:
            base_risk = (
                (wind_speed - WeatherConditionThresholds.CALM) / 10.0 * sensitivity
            )
        elif wind_speed < WeatherConditionThresholds.MODERATE_WIND:
            base_risk = (
                ((wind_speed - WeatherConditionThresholds.LIGHT_BREEZE) / 10.0) * 0.5
                + 10.0
            ) * sensitivity
        else:
            base_risk = min(
                ((wind_speed - WeatherConditionThresholds.MODERATE_WIND) / 10.0 + 20.0)
                * sensitivity,
                100.0,
            )

        return base_risk

    def _calculate_precipitation_risk(self, weather_data: UnifiedForecast) -> float:
        """Calculate precipitation-related risk (0-100)."""
        precip = weather_data.current.get("precipitation", 0.0)

        # Use profile's precipitation sensitivity
        sensitivity = self.profile.precipitation_sensitivity / 100.0

        # Risk increases linearly with precipitation amount
        base_risk = min(precip * 5.0 * sensitivity, 100.0)

        return base_risk

    def _calculate_storm_risk(self, weather_data: UnifiedForecast) -> float:
        """Calculate storm-related risk (0-100)."""
        storm_risk = weather_data.current.get("storm_risk", 0)

        # Use profile's storm sensitivity
        sensitivity = self.profile.storm_sensitivity / 100.0

        # Storm risk is already normalized (0-1)
        return storm_risk * sensitivity * 100.0

    def _calculate_pattern_risk(self, patterns: list) -> float:
        """Calculate risk based on detected weather patterns."""
        if not patterns:
            return 0.0

        # Use profile's pattern sensitivity
        sensitivity = self.profile.pattern_sensitivity / 100.0

        # Calculate maximum pattern severity
        max_severity = max((p.get("severity", 1) for p in patterns), default=0)

        # Map severity (1-5) to risk (0-100)
        base_risk = (max_severity - 1) * 25.0 * sensitivity

        return min(base_risk, 100.0)

    def _apply_profile_sensitivities(
        self, factor_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """Apply profile sensitivities to factor scores."""

        sensitivities = {
            "temperature": self.profile.temperature_sensitivity / 100.0,
            "wind": self.profile.wind_sensitivity / 100.0,
            "precipitation": self.profile.precipitation_sensitivity / 100.0,
            "storm": self.profile.storm_sensitivity / 100.0,
            "pattern": self.profile.pattern_sensitivity / 100.0,
        }

        weighted = {}
        for factor, score in factor_scores.items():
            weight = sensitivities.get(factor, 1.0)
            weighted[factor] = score * weight

        logger.debug(f"Applied profile sensitivities: {weighted}")
        return weighted

    def _calculate_overall_score(self, weighted_scores: Dict[str, float]) -> float:
        """Calculate overall risk score (0-5 scale)."""

        # Get profile thresholds
        thresholds = self.profile

        # Weighted average of all factors
        factors = list(weighted_scores.values())
        average_score = sum(factors) / len(factors)

        # Map 0-100 average to 0-5 scale
        if average_score <= thresholds.very_low_threshold:
            return 1.0  # Very Low
        elif average_score <= thresholds.low_threshold:
            return 2.0  # Low
        elif average_score <= thresholds.moderate_threshold:
            return 3.0  # Moderate
        elif average_score <= thresholds.high_threshold:
            return 4.0  # High
        else:
            return 5.0  # Very High

    def _determine_risk_category(self, score: float) -> RiskCategory:
        """Determine risk category based on score."""
        if score <= 1.0:
            return RiskCategory.VERY_LOW
        elif score <= 2.0:
            return RiskCategory.LOW
        elif score <= 3.0:
            return RiskCategory.MODERATE
        elif score <= 4.0:
            return RiskCategory.HIGH
        else:
            return RiskCategory.VERY_HIGH

    def _determine_alert_level(
        self, score: float, patterns: Optional[list] = None
    ) -> AlertLevel:
        """Determine alert level (0-4) for SkyPulse."""
        if score <= 1.0:
            return AlertLevel.NO_ALERT
        elif score <= 2.0:
            return AlertLevel.MINOR
        elif score <= 3.0:
            return AlertLevel.MODERATE
        elif score <= 4.0:
            return AlertLevel.HIGH
        else:
            return AlertLevel.EXTREME

    def _generate_recommendations(
        self, score: float, category: RiskCategory, factors: Dict[str, float]
    ) -> Dict[str, Any]:
        """Generate operational recommendations."""

        recommendations = []

        # Analyze highest risk factors
        sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)

        # Temperature recommendations
        if factors.get("temperature", 0) > 75.0:
            recommendations.append(
                {
                    "priority": "HIGH" if factors["temperature"] > 85.0 else "MEDIUM",
                    "type": "temperature",
                    "message": "Temperatura extrema detectada",
                    "action": "Monitorear condiciones térmicas",
                }
            )

        # Wind recommendations
        if factors.get("wind", 0) > 75.0:
            recommendations.append(
                {
                    "priority": "HIGH" if factors["wind"] > 85.0 else "MEDIUM",
                    "type": "wind",
                    "message": "Vientos fuertes esperados",
                    "action": "Preparar condiciones de viento",
                }
            )

        # Pattern recommendations
        if factors.get("pattern", 0) > 75.0:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "type": "pattern",
                    "message": "Patrón meteorológico adverso identificado",
                    "action": "Seguir de cerca el desarrollo del patrón",
                }
            )

        return {"count": len(recommendations), "recommendations": recommendations}
