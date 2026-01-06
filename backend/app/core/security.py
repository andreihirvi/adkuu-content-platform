"""
Security utilities for JWT token handling and password hashing.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings


# Password hashing context - using argon2 for modern password hashing
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a hash from a password."""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def validate_token(token: str) -> Dict[str, Any]:
    """
    Validate a JWT token and return payload.

    Args:
        token: JWT token string

    Returns:
        Token payload with user info

    Raises:
        ValueError: If token is invalid or expired
    """
    payload = decode_token(token)

    if payload is None:
        raise ValueError("Invalid or expired token")

    # Check required fields
    user_id = payload.get("user_id") or payload.get("sub")
    if not user_id:
        raise ValueError("Token missing user identifier")

    return {
        "user_id": user_id,
        "is_superuser": payload.get("is_superuser", False),
        "permissions": payload.get("permissions", {}),
        "exp": payload.get("exp")
    }
