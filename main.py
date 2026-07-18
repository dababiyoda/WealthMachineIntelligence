"""Compatibility entrypoint for the canonical UAT governed preview app."""

from src.api.main import app

__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=5000, reload=False)
