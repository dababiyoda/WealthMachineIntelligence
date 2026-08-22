"""The root `jwt.py` stub must never authenticate anyone.

The bypass this guards against was invisible from any single file. `python-jose`
provides `jose.jwt`, nothing in requirements provides a top-level `jwt`, the
Dockerfile copies the repo root into the working directory ahead of
site-packages, and `src/api/auth.py` does a bare `import jwt`. The stub therefore
became the JWT implementation in the shipped image, and it returned a fixed
identity for every input.

Executed against the previous stub, all of these authenticated as `test-user`:
"garbage", "", "AAAA.BBBB.CCCC", an `alg: none` token, and None.
"""
from __future__ import annotations

import importlib
import os

import pytest

import jwt as stub


def _verify_token(token):
    """`verify_token` from src/api/auth.py, reproduced exactly.

    Reproduced rather than imported because importing the module pulls FastAPI
    dependencies that are irrelevant to the property under test. The logic is
    copied verbatim from src/api/auth.py:65-83; if that changes, this must too.
    """
    try:
        payload = stub.decode(token, "any-secret", algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return {"user_id": user_id}
    except stub.ExpiredSignatureError:
        return None
    except stub.JWTError:
        return None


@pytest.mark.parametrize("token", [
    "garbage",
    "",
    "AAAA.BBBB.CCCC",
    "eyJhbGciOiJub25lIn0.eyJzdWIiOiJhZG1pbiJ9.",   # attacker-crafted alg:none
    None,
])
def test_no_token_shape_authenticates(token, monkeypatch):
    """Every input that previously returned an identity must now 401."""
    monkeypatch.delenv("WMI_ALLOW_JWT_STUB", raising=False)
    assert _verify_token(token) is None


def test_the_stub_raises_rather_than_returning_a_forged_identity(monkeypatch):
    """Fail closed, and say why. A silent None would hide the shadowing."""
    monkeypatch.delenv("WMI_ALLOW_JWT_STUB", raising=False)
    with pytest.raises(stub.JWTError) as exc:
        stub.decode("anything", "key")
    assert "validates nothing" in str(exc.value)
    with pytest.raises(stub.JWTError):
        stub.encode({"sub": "admin"}, "key")


def test_the_exception_names_auth_py_catches_actually_exist():
    """src/api/auth.py catches these two by name; the old stub had neither.

    Without them, a real decode failure raised AttributeError *from the except
    clause*, so the error path was broken in a second, independent way.
    """
    assert issubclass(stub.ExpiredSignatureError, stub.JWTError)
    assert issubclass(stub.JWTError, Exception)


def test_the_old_behaviour_requires_an_explicit_opt_in(monkeypatch):
    """The escape hatch exists, is named, and is off unless asked for."""
    monkeypatch.setenv("WMI_ALLOW_JWT_STUB", "1")
    importlib.reload(stub)
    try:
        assert stub.decode("anything", "key") == {"sub": "test-user"}
    finally:
        monkeypatch.delenv("WMI_ALLOW_JWT_STUB", raising=False)
        importlib.reload(stub)


def test_the_stub_is_excluded_from_the_docker_image():
    """Defence in depth: it should not reach a production image at all."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, ".dockerignore"), encoding="utf-8") as fh:
        assert "jwt.py" in fh.read().split()
