"""
User Repository

Simple user repository for Phase 1 security implementation.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


class UserRepository:
    """Simple user repository for demo purposes."""

    def __init__(self, db=None):
        self.db = db
        self._users: Dict[str, Dict[str, Any]] = {}
        self._profiles: Dict[str, Dict[str, Any]] = {}

    def create_user(
        self, username: str, email: str, hashed_password: str
    ) -> Dict[str, Any]:
        """Create a new user."""
        user_id = f"user_{datetime.now().timestamp()}"
        user = {
            "id": user_id,
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "is_active": True,
            "created_at": datetime.now(UTC),
        }
        self._users[username] = user
        logger.info(f"User created: {username}")
        return user

    def create_profile(
        self,
        user_id: str,
        user_type: str,
        location: str = None,
        preferences: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Create user profile."""
        profile = {
            "id": f"profile_{datetime.now().timestamp()}",
            "user_id": user_id,
            "user_type": user_type,
            "location": location,
            "preferences": preferences or {},
            "created_at": datetime.now(UTC),
        }
        self._profiles[user_id] = profile
        logger.info(f"Profile created for user: {user_id}")
        return profile

    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        return self._users.get(username)

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        for user in self._users.values():
            if user.get("email") == email:
                return user
        return None

    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        for user in self._users.values():
            if user.get("id") == user_id:
                return user
        return None

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile."""
        return self._profiles.get(user_id)

    def update_profile(self, user_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Update user profile."""
        profile = self._profiles.get(user_id)
        if profile:
            for key, value in kwargs.items():
                profile[key] = value
            profile["updated_at"] = datetime.now(UTC)
            logger.info(f"Profile updated for user: {user_id}")
        return profile
        return None
