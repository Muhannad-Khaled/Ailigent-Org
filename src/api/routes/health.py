"""
Health Check Routes

Endpoints for system health monitoring.
"""

from fastapi import APIRouter
from datetime import datetime

from src.config import settings
from src.integrations.odoo.client import get_odoo_client

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version
    }


@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check with component status."""
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "components": {}
    }

    # Check Odoo connection
    try:
        client = get_odoo_client()
        version = client.get_version()
        health["components"]["odoo"] = {
            "status": "healthy",
            "version": version.get("server_version", "unknown")
        }
    except Exception as e:
        health["components"]["odoo"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "degraded"

    # Check agent system
    try:
        from src.agents.supervisor import get_agent_application
        app = get_agent_application()
        health["components"]["agents"] = {
            "status": "healthy",
            "message": "Agent system initialized"
        }
    except Exception as e:
        health["components"]["agents"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "degraded"

    return health
