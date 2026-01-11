"""
Authentication Service

User authentication, registration, and profile management.
"""

import logging
from typing import Optional
from datetime import datetime, UTC, timedelta

from app.models.auth import UserCreate, UserProfileCreate
from app.utils.security import get_password_hash, verify_password, create_access_token
from app.data.repositories.user_repository import get_user_repository

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service."""

    def __init__(self, db=None):
        # For now, use in-memory storage for demo
        self.db = db
        # Usar repositorio compartido para que todas las instancias compartan los mismos usuarios
        self.user_repo = get_user_repository()

    async def create_user(
        self, user_data: UserCreate, profile_data: UserProfileCreate
    ) -> dict:
        """Create a new user with profile."""
        try:
            # Check if user already exists
            existing_user = self.user_repo.get_by_username(user_data.username)
            if existing_user:
                raise ValueError(f"Username {user_data.username} already exists")
            
            existing_email = self.user_repo.get_by_email(user_data.email)
            if existing_email:
                raise ValueError(f"Email {user_data.email} already exists")

            # Hash password before storing
            hashed_password = get_password_hash(user_data.password)

            # Create user in repository
            user = self.user_repo.create_user(
                username=user_data.username,
                email=user_data.email,
                hashed_password=hashed_password
            )

            # Create profile
            profile = self.user_repo.create_profile(
                user_id=user["id"],
                user_type=profile_data.user_type.value if hasattr(profile_data.user_type, 'value') else str(profile_data.user_type),
                location=profile_data.location,
                preferences=profile_data.preferences
            )

            # Generate access token
            token_data = {"sub": user_data.username}
            access_token = create_access_token(token_data)

            logger.info(f"User created successfully: {user_data.username}")

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user["id"],
                    "username": user_data.username,
                    "email": user_data.email,
                    "profile": profile,
                },
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise

    async def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user and return token."""
        try:
            # Validate input
            if not username or not password:
                logger.warning("Authentication attempt with empty username or password")
                return None

            # Get user from repository
            user = self.user_repo.get_by_username(username)
            if not user:
                logger.warning(f"Authentication failed: user '{username}' not found")
                return None

            # Verify password against stored hash
            stored_hash = user.get("hashed_password")
            if not stored_hash:
                logger.warning(f"User '{username}' has no password hash stored")
                return None

            if not verify_password(password, stored_hash):
                logger.warning(f"Authentication failed: incorrect password for user '{username}'")
                return None

            # Generate access token only if credentials are valid
            token_data = {"sub": username}
            access_token = create_access_token(token_data)

            logger.info(f"User authenticated successfully: {username}")

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                },
            }

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
