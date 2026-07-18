"""
Authentication and authorization module
JWT token handling and user management
"""
import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

try:  # pragma: no cover - dependency may be unavailable in tests
    from passlib.context import CryptContext  # type: ignore
except Exception:  # pragma: no cover - fallback when passlib backend missing
    CryptContext = None  # type: ignore

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from src.logging_config import logger

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") if CryptContext else None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def demo_auth_enabled() -> bool:
    """Return whether local demo identities were explicitly enabled."""

    return (
        os.getenv("ENVIRONMENT", "development").lower() != "production"
        and os.getenv("ALLOW_DEMO_AUTH", "false").lower() == "true"
    )


def validate_auth_configuration() -> None:
    """Fail production startup when authentication uses unsafe defaults."""

    if os.getenv("ENVIRONMENT", "development").lower() != "production":
        return
    unsafe_secrets = {"", "change-me", "your-secret-key-change-in-production"}
    if SECRET_KEY in unsafe_secrets or len(SECRET_KEY) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be a non-default 32+ character secret")
    if os.getenv("ALLOW_DEMO_AUTH", "false").lower() == "true":
        raise RuntimeError("demo authentication cannot be enabled in production")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""

    if hashed_password.startswith("plaintext::"):
        return plain_password == hashed_password.split("::", 1)[1]

    if pwd_context:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            logger.warning("Falling back to plaintext password verification")
    return plain_password == hashed_password

def get_password_hash(password: str) -> str:
    """Hash a password using passlib if available."""

    if pwd_context:
        try:
            return pwd_context.hash(password)
        except Exception:
            logger.warning("Passlib backend not available; using plaintext hash")
    return f"plaintext::{password}"

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return {
            "user_id": user_id,
            "username": payload.get("username"),
            "role": payload.get("role", "user"),
            "permissions": payload.get("permissions", [])
        }
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.JWTError as e:
        logger.warning("JWT decode error", error=str(e))
        return None

# For demo purposes - in production, integrate with real user database
DEMO_USERS = {
    "admin": {
        "user_id": "admin-123",
        "username": "admin", 
        "password_hash": get_password_hash("admin"),
        "role": "admin",
        "permissions": ["read", "write", "admin"]
    },
    "demo": {
        "user_id": "demo-456",
        "username": "demo",
        "password_hash": get_password_hash("demo"),
        "role": "user", 
        "permissions": ["read"]
    }
}

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a user with username/password"""
    if not demo_auth_enabled():
        return None
    user = DEMO_USERS.get(username)
    if not user:
        return None
    
    if not verify_password(password, user["password_hash"]):
        return None
    
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "permissions": user["permissions"]
    }


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Retrieve the current user based on the access token."""

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
        )

    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    user = DEMO_USERS.get(payload.get("username", ""))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "permissions": user["permissions"],
    }


async def require_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Require an authenticated human administrative identity."""

    permissions = set(current_user.get("permissions", []))
    if current_user.get("role") != "admin" or "admin" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Human administrator authority required",
        )
    return current_user
