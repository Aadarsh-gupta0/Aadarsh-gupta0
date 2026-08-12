"""HTTP API routers."""

from .admin import router as admin_router
from .devices import router as devices_router
from .jobs import router as jobs_router

__all__ = ["admin_router", "devices_router", "jobs_router"]
