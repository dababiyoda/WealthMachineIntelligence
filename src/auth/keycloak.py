"""
Keycloak JWT authentication and verification utilities.

This module fetches JSON Web Keys (JWKS) from Keycloak and verifies
JSON Web Tokens (JWTs) using the appropriate public key. It raises
KeycloakAuthError on validation errors such as signature mismatch,
expiration, or audience mismatch.
"""
from typing import Dict, Any, List, Optional
import time
import requests
from jose import jwk, jwt
from jose.utils import base64url_decode

from ..config import settings


class KeycloakAuthError(Exception):
    """Exception raised for errors during Keycloak JWT verification."""


def get_jwks() -> Dict[str, Any]:
    """Fetch the JWKS from the Keycloak server for the configured realm."""
    jwks_url = (
        f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}"
        f"/protocol/openid-connect/certs"
    )
    response = requests.get(jwks_url, timeout=5)
    response.raise_for_status()
    return response.json()


def verify_token(token: str) -> Dict[str, Any]:
    """Verify a JWT issued by Keycloak and return its claims.

    Args:
        token: The JWT string to verify.

    Returns:
        Decoded token claims as a dictionary.

    Raises:
        KeycloakAuthError: If the token is invalid, expired, or fails verification.
    """
    # Retrieve JWKS and header info
    jwks = get_jwks()
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    if not kid:
        raise KeycloakAuthError("Invalid token header: missing 'kid'.")

    # Find the matching key by kid
    key_data = next((key for key in jwks.get("keys", []) if key.get("kid") == kid), None)
    if not key_data:
        raise KeycloakAuthError("Unable to find matching JWK for token.")

    # Construct JWK and verify signature
    public_key = jwk.construct(key_data)
    message, encoded_signature = token.rsplit(".", 1)
    decoded_signature = base64url_decode(encoded_signature.encode())
    if not public_key.verify(message.encode(), decoded_signature):
        raise KeycloakAuthError("Token signature verification failed.")

    # Decode claims without verification to inspect expiry and audience
    claims = jwt.get_unverified_claims(token)

    # Check expiration
    exp = claims.get("exp")
    if exp is not None and exp < time.time():
        raise KeycloakAuthError("Token has expired.")

    # Check audience
    aud = claims.get("aud")
    if aud and aud != settings.keycloak_client_id:
        raise KeycloakAuthError("Token audience mismatch.")

    return claims
