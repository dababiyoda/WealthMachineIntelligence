"""Inert JWT stub. Present for lineage; refuses to authenticate anything.

WHAT THIS FILE USED TO DO, AND WHY IT WAS DANGEROUS

This module previously exposed `decode()` returning `{"sub": "test-user"}` for
ANY input — any string, the empty string, a malformed token, an attacker-crafted
`alg: none` token, even `None`. That is benign in a test process and catastrophic
in the shipped image, because of a chain that is invisible from any single file:

  1. `requirements.txt` installs `python-jose`, which provides `jose.jwt`.
     NOTHING in requirements provides a top-level `jwt` module (PyJWT: 0 entries).
  2. `Dockerfile` does `WORKDIR /app` then `COPY . .`, placing this file in the
     working directory, which precedes site-packages on `sys.path` for the
     `uvicorn main:app` entrypoint.
  3. `src/api/auth.py` does a bare `import jwt` — and binds THIS file.
  4. Every route gated by `verify_token` therefore accepted any bearer token.

Executed against the previous stub, all of these authenticated as `test-user`:
`"garbage"`, `""`, `"AAAA.BBBB.CCCC"`, an `alg: none` token, and `None`.

WHY THE FILE IS KEPT RATHER THAN DELETED

Deleting it would make `import jwt` raise ImportError at startup — a louder
failure, but it also destroys the record of why this file existed. The
institution's preservation rule is to render superseded code inert and keep its
lineage, not to erase it.

WHAT IT DOES NOW

`decode()` and `encode()` raise `JWTError` unless `WMI_ALLOW_JWT_STUB=1` is set
explicitly in the environment. `verify_token` in `src/api/auth.py` already
catches `JWTError` and returns `None`, so a request that previously authenticated
now receives a clean 401 instead of a forged identity.

The exception classes exist for a second reason: `src/api/auth.py` references
`jwt.ExpiredSignatureError` and `jwt.JWTError` in its `except` clauses, and the
previous stub defined neither. Any real decode failure would have raised
`AttributeError` from the except clause itself. Those names are now present.

THIS IS NOT THE WHOLE FIX. The correct long-term change is for `src/api/auth.py`
to import the installed library explicitly (`from jose import jwt`) so no
top-level shadow can ever bind. That touches authentication logic and is left to
the repo's owner. This change removes the bypass without changing auth behaviour
for any legitimate token, because there were no legitimate tokens: the stub
validated nothing.
"""

import os
from typing import Any, Dict

#: Opt-in, explicit, and off by default. An environment that wants the old
#: behaviour has to ask for it by name, in the environment, every time.
_STUB_ENV = "WMI_ALLOW_JWT_STUB"


class JWTError(Exception):
    """Base error. `src/api/auth.py` catches this and returns None."""


class ExpiredSignatureError(JWTError):
    """Referenced by `src/api/auth.py`; absent from the previous stub."""


def _stub_enabled() -> bool:
    return os.getenv(_STUB_ENV) == "1"


def _refuse(operation: str) -> None:
    raise JWTError(
        f"jwt stub refuses to {operation}: this module validates nothing and is "
        f"not a JWT implementation. It is shadowing the installed library "
        f"(python-jose provides `jose.jwt`, not `jwt`). Set {_STUB_ENV}=1 only "
        f"in a test process that genuinely wants an unvalidated token."
    )


def encode(payload: Dict[str, Any], key: str, algorithm: str = "HS256") -> str:
    if not _stub_enabled():
        _refuse("encode")
    return "stub-token"


def decode(token: str, key: str, algorithms: Any | None = None) -> Dict[str, Any]:
    if not _stub_enabled():
        _refuse("decode")
    return {"sub": "test-user"}
