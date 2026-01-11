"""
SkyPulse Security Infrastructure

Core utilities for authentication, JWT handling, and API key management.
"""

import os
import secrets
import logging
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any

import jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# Password hashing
# Configure bcrypt with explicit settings to avoid initialization issues
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__ident="2b",  # Use bcrypt 2b identifier
    bcrypt__rounds=12,   # Standard number of rounds
)

# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# API key store (in production, use proper key management)
API_KEYS = {
    "windy": os.getenv("WINDY_POINT_FORECAST_API_KEY"),
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    # Ensure password is a string, not bytes
    if isinstance(password, bytes):
        password = password.decode('utf-8')
    
    # Bcrypt has a 72-byte limit, ensure we don't exceed it
    # Convert to bytes to check actual byte length (not character length)
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # Truncate to 72 bytes, but try to avoid breaking UTF-8 characters
        # Take first 72 bytes and decode, ignoring any incomplete characters
        truncated_bytes = password_bytes[:72]
        # Find the last valid UTF-8 character boundary
        while truncated_bytes and truncated_bytes[-1] & 0xC0 == 0x80:
            truncated_bytes = truncated_bytes[:-1]
        password = truncated_bytes.decode('utf-8', errors='ignore')
    
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    logger.info(f"Access token created for user: {data.get('sub', 'unknown')}")
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.JWTError:
        logger.warning("Invalid token")
        return None


def get_api_key(service: str) -> Optional[str]:
    """Get API key for a service."""
    key = API_KEYS.get(service)
    if not key:
        logger.error(f"No API key configured for service: {service}")
    return key


def mask_api_key(api_key: str) -> str:
    """Mask API key for logging."""
    if len(api_key) <= 8:
        return "***"
    return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
