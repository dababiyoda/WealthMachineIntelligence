"""WMI JWT admission adapted from PR #23; no issuer or demo identities.

Signed claims establish a principal, not founder or Kernel authority.
Shared HS256 holders are not mutually isolated identities.
"""
import os
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def _configuration() -> tuple[str, str, str]:
    key = os.environ.get("JWT_SECRET_KEY", "")
    issuer = os.environ.get("JWT_ISSUER", "")
    audience = os.environ.get("JWT_AUDIENCE", "")
    if (len(key.strip()) < 32 or key == "your-secret-key-change-in-production"
            or not issuer.strip() or not audience.strip()):
        raise RuntimeError("Explicit JWT signing key (32+ characters), issuer and audience required")
    return key, issuer, audience


def validate_auth_configuration() -> None:
    """Every environment fails closed; development flags cannot bypass."""
    _configuration()


def verify_token(token: str) -> dict[str, Any] | None:
    key, issuer, audience = _configuration()
    if not isinstance(token, str) or not token:
        return None
    try:
        payload = jwt.decode(
            token, key, algorithms=[ALGORITHM], issuer=issuer, audience=audience,
            options={"require_exp": True, "require_sub": True,
                     "require_iss": True, "require_aud": True},
        )
        subject = payload.get("sub")
        role = payload.get("role", "user")
        permissions = payload.get("permissions", [])
        username = payload.get("username")
        if not isinstance(subject, str) or not subject.strip():
            return None
        if not isinstance(role, str) or not role.strip():
            return None
        if not isinstance(permissions, list) or not all(
            isinstance(p, str) and p.strip() for p in permissions
        ):
            return None
        if username is not None and not isinstance(username, str):
            return None
        if any(name in payload and type(payload[name]) is not int
               for name in ("exp", "iat", "nbf")):
            return None
        return {"user_id": subject, "username": username,
                "role": role, "permissions": permissions}
    except (JWTError, ValueError, TypeError, OverflowError):
        return None


async def get_current_user(token: str | None = Depends(oauth2_scheme)) -> dict[str, Any]:
    if not token:
        raise HTTPException(401, "Authentication credentials required",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        principal = verify_token(token)
    except RuntimeError:
        raise HTTPException(503, "Authentication unavailable") from None
    if principal is None:
        raise HTTPException(401, "Invalid authentication credentials",
                            headers={"WWW-Authenticate": "Bearer"})
    return principal
