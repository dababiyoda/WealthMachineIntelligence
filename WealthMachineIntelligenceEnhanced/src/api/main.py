from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from ..database.connection import create_tables, get_db
from ..cache import get_cache
from ..vector_db import get_vector_store
from ..auth.keycloak import verify_token
from .routes import ventures


app = FastAPI(title="WealthMachine Intelligence Enhanced")

# Configure CORS to allow cross-origin requests from any domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """Initialise database tables on application startup."""
    create_tables()


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/cache/{key}", tags=["cache"])
def read_cache(
    key: str,
    cache=Depends(get_cache),
    token: str = Depends(verify_token),
) -> dict[str, str]:
    """Retrieve a value from the cache."""
    value = cache.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Not found")
    return {"key": key, "value": value}


@app.post("/vector/search", tags=["vector"])
def vector_search(
    embedding: List[float],
    top_k: int = 5,
    vector_store=Depends(get_vector_store),
    token: str = Depends(verify_token),
) -> list:
    """Search similar vectors in the vector store."""
    results = vector_store.search(embedding, top_k=top_k)
    return results


# Include venture routes under /ventures path
app.include_router(ventures.router, prefix="/ventures", tags=["ventures"])
