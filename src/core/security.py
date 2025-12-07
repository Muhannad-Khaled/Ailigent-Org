"""
Security Utilities

Authentication, authorization, and security helpers.
"""

import hmac
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify

    Returns:
        Decoded payload

    Raises:
        JWTError: If token is invalid or expired
    """
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])


def verify_telegram_webhook(
    token: str,
    received_hash: str,
    data: bytes
) -> bool:
    """
    Verify Telegram webhook request authenticity.

    Args:
        token: Bot token
        received_hash: Hash received in request header
        data: Request body bytes

    Returns:
        True if verification passes
    """
    secret_key = hashlib.sha256(token.encode()).digest()
    calculated_hash = hmac.new(
        secret_key,
        data,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(calculated_hash, received_hash)


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def generate_thread_id() -> str:
    """Generate a unique thread ID for conversations."""
    return secrets.token_hex(16)
