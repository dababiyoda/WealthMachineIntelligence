"""Compatibility entrypoint: canonical source src.api.main, owner WMI API.

Supports main:app and python main.py. Expiry: packaged consumers migrate.
Removal: all consumer migrations and composition parity tests pass.
Failure: propagate imports/configuration errors, never start a fallback.
Old generation: historical/root-main-ec84b6a2.py.txt (never imported).
"""
from src.api.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=5000)
