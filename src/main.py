"""
Multi-Agent Enterprise System

FastAPI application entry point with LangGraph agent system,
Odoo ERP integration, and Telegram bot support.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.core.logging import setup_logging, get_logger
from src.api.routes import (
    health_router,
    agents_router,
    contracts_router,
    hr_router,
    finance_router,
    telegram_router
)
from src.api.routes.telegram import set_bot_manager

# Setup logging
setup_logging(level=settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown of services like the Telegram bot.
    """
    logger.info("Starting Multi-Agent Enterprise System...")

    # Initialize Telegram bot if token is configured AND we have a real webhook URL
    # Skip webhook setup for local development (when using placeholder URL)
    is_valid_webhook = (
        settings.webhook_url and
        settings.webhook_url != "https://your-domain.com" and
        not settings.webhook_url.startswith("https://your-")
    )

    if settings.telegram_bot_token and is_valid_webhook:
        try:
            from src.integrations.telegram.bot import get_bot_manager
            bot_manager = get_bot_manager()
            await bot_manager.initialize()
            await bot_manager.start()
            set_bot_manager(bot_manager)
            logger.info("Telegram bot started successfully")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
    else:
        logger.info("Telegram webhook skipped - use run_bot.py for polling mode")

    # Initialize Odoo connection
    try:
        from src.integrations.odoo.client import get_odoo_client
        client = get_odoo_client()
        client.authenticate()
        logger.info("Odoo connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Odoo: {e}")

    # Initialize agent system
    try:
        from src.agents.supervisor import get_agent_application
        get_agent_application()
        logger.info("Agent system initialized")
    except Exception as e:
        logger.error(f"Failed to initialize agent system: {e}")

    logger.info("System startup complete")

    yield

    # Shutdown
    logger.info("Shutting down...")

    if settings.telegram_bot_token:
        try:
            from src.integrations.telegram.bot import get_bot_manager
            bot_manager = get_bot_manager()
            await bot_manager.stop()
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")

    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Multi-Agent Enterprise System with LangGraph orchestration, "
        "Odoo ERP integration, and Telegram bot support."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(agents_router)
app.include_router(contracts_router)
app.include_router(hr_router)
app.include_router(finance_router)
app.include_router(telegram_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
