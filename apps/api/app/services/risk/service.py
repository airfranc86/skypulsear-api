"""
Risk Service - Main Risk Scoring Module

Unified risk scoring service that orchestrates all risk calculation modules.
This replaces the monolithic risk_scoring.py (736 lines) with modular architecture.
"""

import logging
from typing import Dict, Any, Optional

from app.services.risk.profiles import (
    UserProfile,
    ProfileConfigurations,
    RiskProfileConfig,
)
from app.services.risk.calculator import RiskCalculator
from app.services.risk.factors import RiskFactors
from app.data.schemas.normalized_weather import UnifiedForecast
from app.services.alert_service import AlertLevel

logger = logging.getLogger(__name__)


class RiskScoringService:
    """
    Main risk scoring service for SkyPulse.

    Orchestrates all risk calculation modules:
    - RiskProfiles: Profile configurations
    - RiskFactors: Individual factor calculations
    - RiskCalculator: Core calculation logic
    """

    def __init__(self, profile: UserProfile = UserProfile.GENERAL):
        """Initialize risk scoring service with user profile."""
        self.profile = profile

        # Get profile configuration
        self.profile_config = ProfileConfigurations.get_profile(profile)

        # Initialize calculator with profile config
        self.calculator = RiskCalculator(self.profile_config)

    def calculate_risk(
        self, weather_data: UnifiedForecast, detected_patterns: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive risk assessment.

        Args:
            weather_data: Normalized weather forecast
            detected_patterns: List of detected weather patterns

        Returns:
            Complete risk assessment with score, alerts, and recommendations
        """
        logger.info(f"Calculating risk for profile: {self.profile_config.profile_name}")

        # Calculate individual factors using RiskFactors module
        factor_scores = RiskFactors.calculate_all_factors(
            weather_data, self.profile_config
        )

        # Calculate weighted scores using calculator
        weighted_scores = self.calculator.calculate_risk_score(
            weather_data, detected_patterns
        )

        # Generate complete risk assessment
        result = {
            **weighted_scores,
            "profile": self.profile.value,
            "profile_name": self.profile_config.profile_name,
            "profile_config": self.profile_config.model_dump(),
            "recommendations": weighted_scores.get("recommendations", {}),
            "calculated_at": weighted_scores.get("calculated_at"),
        }

        logger.info(f"Risk calculation complete: {result['overall_score']:.1f}")
        return result

    def calculate_risk_for_location(
        self, lat: float, lon: float, hours_ahead: int = 6
    ) -> Dict[str, Any]:
        """
        Calculate risk for specific location.

        Args:
            lat: Latitude
            lon: Longitude
            hours_ahead: Hours ahead to forecast

        Returns:
            Risk assessment for the location
        """
        logger.info(f"Calculating risk for location: {lat}, {lon}")

        # This would call weather service to get forecast data
        # For now, return placeholder
        return {
            "overall_score": 2.0,
            "risk_level": "low",
            "profile": self.profile.value,
            "recommendations": [],
            "calculated_at": "2024-01-07T00:00:00Z",
        }

    def get_available_profiles(self) -> list[dict[str, Any]]:
        """
        Get list of all available risk profiles.

        Returns:
            List of available profiles with their descriptions
        """
        profiles = []

        for profile in UserProfile:
            config = ProfileConfigurations.get_profile(profile)
            profiles.append(
                {
                    "profile": profile.value,
                    "profile_name": config.profile_name,
                    "description": config.description,
                }
            )

        logger.info(f"Available profiles: {[p['profile_name'] for p in profiles]}")
        return profiles

    def change_profile(self, new_profile: UserProfile):
        """
        Change the risk profile for this service.

        Args:
            new_profile: New UserProfile enum value
        """
        self.profile = new_profile
        self.profile_config = ProfileConfigurations.get_profile(new_profile)
        self.calculator = RiskCalculator(self.profile_config)

        logger.info(f"Profile changed to: {new_profile.value}")

    def get_profile_summary(self) -> Dict[str, Any]:
        """
        Get summary of current profile configuration.

        Returns:
            Profile summary including thresholds and sensitivities
        """
        return {
            "profile": self.profile.value,
            "profile_name": self.profile_config.profile_name,
            "description": self.profile_config.description,
            "thresholds": {
                "very_low": self.profile_config.very_low_threshold,
                "low": self.profile_config.low_threshold,
                "moderate": self.profile_config.moderate_threshold,
                "high": self.profile_config.high_threshold,
                "very_high": self.profile_config.very_high_threshold,
            },
            "sensitivities": {
                "temperature": self.profile_config.temperature_sensitivity,
                "wind": self.profile_config.wind_sensitivity,
                "precipitation": self.profile_config.precipitation_sensitivity,
                "storm": self.profile_config.storm_sensitivity,
                "pattern": self.profile_config.pattern_sensitivity,
            },
        }
