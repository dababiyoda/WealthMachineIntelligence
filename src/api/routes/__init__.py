"""Collection of FastAPI routers.

Each submodule exposes an ``APIRouter`` that groups related endpoints.
The main application imports these routers and mounts them under a
versioned prefix. Keeping them in a dedicated package keeps the API
organization clear.
"""