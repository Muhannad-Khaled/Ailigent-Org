"""API route modules."""

from .health import router as health_router
from .agents import router as agents_router
from .contracts import router as contracts_router
from .hr import router as hr_router
from .finance import router as finance_router
from .telegram import router as telegram_router

__all__ = [
    "health_router",
    "agents_router",
    "contracts_router",
    "hr_router",
    "finance_router",
    "telegram_router"
]
