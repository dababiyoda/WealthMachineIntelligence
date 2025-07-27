"""Integration with Keycloak or Ory Kratos.

This module provides helper functions to verify and decode JWT access tokens
issued by an external identity provider.  In production you should validate
the token signature, issuer and audience using the provider’s public keys.
For simplicity, this implementation demonstrates how to fetch the JSON Web
Key Set (JWKS) from the issuer and verify tokens.

If you use Ory Kratos instead of Keycloak, the `ORY_URL` environment
variable should point to the Kratos public API and you can adjust the
functions accordingly.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Dict, Any

import httpx
import jwt

from ..config import get_settings

logger = logging.getLogger(__name__)


@lru_cache()
def _get_jwks() -> Dict[str, Any]:
    """Fetch the JSON Web Key Set from the identity provider."""
    settings = get_settings()
    issuer = settings.auth_issuer_url.rstrip("/")
    jwks_url = f"{issuer}/protocol/openid-connect/certs"
    resp = httpx.get(jwks_url, timeout=5)
    resp.raise_for_status()
    return resp.json()


def verify_token(token: str) -> Dict[str, Any]:
    """Verify a JWT and return its claims.

    Raises `jwt.PyJWTError` if verification fails.
    """
    jwks = _get_jwks()
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    key = next((key for key in jwks["keys"] if key["kid"] == kid), None)
    if key is None:
        raise jwt.InvalidTokenError("Unable to find matching JWK for token")
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
    settings = get_settings()
    claims = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=settings.auth_client_id,
        issuer=settings.auth_issuer_url,
    )
    return claims
