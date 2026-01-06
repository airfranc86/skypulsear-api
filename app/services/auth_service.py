"""
Authentication Service

User authentication, registration, and profile management.
"""

import logging
from typing import Optional
from datetime import datetime, UTC, timedelta

from app.models.auth import UserCreate, UserProfileCreate
from app.utils.security import get_password_hash, verify_password, create_access_token
from app.data.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service."""

    def __init__(self, db=None):
        # For now, use in-memory storage for demo
        self.db = db
        self.user_repo = UserRepository(db)

    async def create_user(
        self, user_data: UserCreate, profile_data: UserProfileCreate
    ) -> dict:
        """Create a new user with profile."""
        try:
            # For demo: simple in-memory storage
            # In production, this would use database
            user_id = f"user_{datetime.now().timestamp()}"

            # Generate access token
            token_data = {"sub": user_data.username}
            access_token = create_access_token(token_data)

            logger.info(f"User created successfully: {user_data.username}")

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user_id,
                    "username": user_data.username,
                    "email": user_data.email,
                    "profile": profile_data.dict(),
                },
            }

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise

    async def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user and return token."""
        try:
            # For demo: simple validation
            # In production, this would validate against database
            if not username or not password:
                return None

            # Generate access token (for demo, always succeed with proper credentials)
            if len(password) >= 8:  # Basic validation
                token_data = {"sub": username}
                access_token = create_access_token(token_data)

                logger.info(f"User authenticated successfully: {username}")

                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": {
                        "id": f"user_{username}",
                        "username": username,
                        "email": f"{username}@example.com",
                    },
                }

            return None

        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None

    async def get_user_profile(self, user_id: str) -> Optional[dict]:
        """Get user profile."""
        try:
            # For demo: return profile
            logger.info(f"Getting profile for user: {user_id}")

            return {
                "user": {
                    "id": user_id,
                    "username": "demo_user",
                    "email": "demo@example.com",
                    "is_active": True,
                },
                "profile": {
                    "user_type": "general",
                    "location": "Córdoba, Argentina",
                    "preferences": {},
                },
            }

        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
