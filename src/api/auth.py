"""Fail-closed JWT authentication for the governed preview.

Local demo identities exist only when explicitly enabled (or outside a
production environment).  Production requires a strong signing secret and an
operator credential supplied through environment secrets.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import hmac
import os
import secrets
from typing import Any, Callable, Optional
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError, decode, encode

from src.logging_config import logger


ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
ALGORITHM = "HS256"
ISSUER = "uat-governed-preview"
AUDIENCE = "uat-operator"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
_DEVELOPMENT_SECRET = "local-simulation-secret-not-for-production"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", _DEVELOPMENT_SECRET)

if ENVIRONMENT == "production" and (
    SECRET_KEY == _DEVELOPMENT_SECRET or len(SECRET_KEY) < 32
):
    raise RuntimeError("production JWT_SECRET_KEY must contain at least 32 characters")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_password_hash(password: str, salt: str | None = None) -> str:
    """Return a portable PBKDF2-SHA256 password record."""

    salt = salt or secrets.token_hex(16)
    iterations = 310_000
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(plain_password: str, encoded_password: str) -> bool:
    """Verify a PBKDF2 record without plaintext or permissive fallback."""

    try:
        algorithm, iteration_text, salt, expected = encoded_password.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            bytes.fromhex(salt),
            int(iteration_text),
        ).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


_LOCAL_PASSWORDS = {
    "admin": get_password_hash("admin", salt="00" * 16),
    "demo": get_password_hash("demo", salt="11" * 16),
}


@lru_cache(maxsize=1)
def _configured_users_snapshot() -> dict[str, dict[str, Any]]:
    """Build the process identity snapshot once to avoid per-request PBKDF2 work."""

    users: dict[str, dict[str, Any]] = {}
    if _bool_env("UAT_ALLOW_DEMO_USERS", ENVIRONMENT != "production"):
        users.update(
            {
                "admin": {
                    "user_id": "admin-123",
                    "username": "admin",
                    "password_hash": _LOCAL_PASSWORDS["admin"],
                    "role": "admin",
                    "permissions": [
                        "read",
                        "write",
                        "approve",
                        "governance:admin",
                        "kill-switch:activate",
                        "kill-switch:release",
                    ],
                    "identity_source": "local_preview_only",
                },
                "demo": {
                    "user_id": "demo-456",
                    "username": "demo",
                    "password_hash": _LOCAL_PASSWORDS["demo"],
                    "role": "reviewer",
                    "permissions": ["read", "write:evidence", "verify"],
                    "identity_source": "local_preview_only",
                },
            }
        )

    operator_username = os.getenv("UAT_OPERATOR_USERNAME")
    operator_password = os.getenv("UAT_OPERATOR_PASSWORD")
    if operator_username and operator_password:
        users[operator_username] = {
            "user_id": os.getenv("UAT_OPERATOR_ID", "operator-primary"),
            "username": operator_username,
            "password_hash": get_password_hash(
                operator_password,
                salt=hashlib.sha256(operator_username.encode("utf-8")).hexdigest()[:32],
            ),
            "role": "admin",
            "permissions": [
                "read",
                "write",
                "approve",
                "governance:admin",
                "kill-switch:activate",
                "kill-switch:release",
            ],
            "identity_source": "environment_operator",
        }
    return users


def configured_users() -> dict[str, dict[str, Any]]:
    """Return an isolated copy of the explicit process identity snapshot."""

    return {
        username: {
            **record,
            "permissions": list(record["permissions"]),
        }
        for username, record in _configured_users_snapshot().items()
    }


# Compatibility name for existing imports. Environment-backed preview
# credentials are snapshotted for the process lifetime; rotation requires a
# controlled restart.
DEMO_USERS = configured_users()


def create_access_token(
    data: dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    claims = data.copy()
    claims.update(
        {
            "iat": now,
            "nbf": now,
            "exp": expire,
            "iss": ISSUER,
            "aud": AUDIENCE,
            "jti": str(uuid4()),
        }
    )
    return encode(claims, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict[str, Any]]:
    try:
        payload = decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={
                "require": ["sub", "username", "iat", "nbf", "exp", "iss", "aud", "jti"]
            },
        )
        if not payload.get("sub") or not payload.get("username"):
            return None
        return {
            "user_id": payload["sub"],
            "username": payload["username"],
            "role": payload.get("role", "user"),
            "permissions": payload.get("permissions", []),
            "jti": payload.get("jti"),
        }
    except ExpiredSignatureError:
        logger.warning("Token expired")
    except InvalidTokenError as exc:
        logger.warning("JWT decode error", error=str(exc))
    return None


def authenticate_user(username: str, password: str) -> Optional[dict[str, Any]]:
    user = configured_users().get(username)
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "permissions": user["permissions"],
        "identity_source": user["identity_source"],
    }


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
) -> dict[str, Any]:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    current = configured_users().get(payload["username"])
    if not current or current["user_id"] != payload["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identity is no longer active",
        )
    return {
        "user_id": current["user_id"],
        "username": current["username"],
        "role": current["role"],
        "permissions": current["permissions"],
        "identity_source": current["identity_source"],
    }


def require_permissions(*required: str) -> Callable[..., Any]:
    async def dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        missing = set(required) - set(user.get("permissions", []))
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(sorted(missing))}",
            )
        return user

    return dependency


def require_any_permission(*allowed: str) -> Callable[..., Any]:
    async def dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if not set(allowed) & set(user.get("permissions", [])):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these permissions is required: {', '.join(sorted(allowed))}",
            )
        return user

    return dependency


__all__ = [
    "DEMO_USERS",
    "authenticate_user",
    "configured_users",
    "create_access_token",
    "get_current_user",
    "get_password_hash",
    "require_any_permission",
    "require_permissions",
    "verify_password",
    "verify_token",
]
