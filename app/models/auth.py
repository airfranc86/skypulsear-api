"""
Authentication Models

Pydantic models for user authentication, profiles, and API key management.
"""

from pydantic import BaseModel, Field, EmailStr
from pydantic.v1 import EmailStr as EmailStrV1
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class UserType(str, Enum):
    """User types for SkyPulse."""

    GENERAL = "general"
    AGRICULTURE = "agriculture"
    AVIATION = "aviation"
    CONSTRUCTION = "construction"
    TOURISM = "tourism"


class UserBase(BaseModel):
    """Base user model."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    """User creation model."""

    password: str = Field(..., min_length=8, max_length=100)


class UserResponse(UserBase):
    """User response model."""

    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data model."""

    username: Optional[str] = None


class UserProfile(BaseModel):
    """User profile model."""

    user_type: UserType
    location: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class UserProfileCreate(UserProfile):
    """User profile creation model."""

    pass


class UserProfileResponse(UserProfile):
    """User profile response model."""

    id: int
    user_id: int

    class Config:
        from_attributes = True


class APIKeyRequest(BaseModel):
    """API key request model."""

    service: str = Field(..., pattern="^(windy|meteosource)$")


class APIKeyResponse(BaseModel):
    """API key response model."""

    api_key: str
    service: str
    expires_at: Optional[datetime] = None
    rate_limit: int
