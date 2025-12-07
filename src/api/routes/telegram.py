"""
Telegram Webhook Routes

Endpoints for Telegram bot integration.
"""

from fastapi import APIRouter, Request, Response, HTTPException
import logging

router = APIRouter(prefix="/telegram", tags=["Telegram"])
logger = logging.getLogger(__name__)

# Telegram bot manager will be set by the main app
_bot_manager = None


def set_bot_manager(manager):
    """Set the Telegram bot manager instance."""
    global _bot_manager
    _bot_manager = manager


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Receive and process Telegram webhook updates.

    This endpoint receives updates from Telegram and routes them
    to the appropriate handler.
    """
    try:
        if _bot_manager is None:
            logger.warning("Telegram bot manager not initialized")
            return Response(status_code=200)

        update_data = await request.json()
        await _bot_manager.process_update(update_data)

        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        # Return 200 to prevent Telegram from retrying
        return Response(status_code=200)


@router.get("/webhook/status")
async def webhook_status():
    """Check webhook configuration status."""
    if _bot_manager is None:
        return {
            "status": "not_configured",
            "message": "Telegram bot manager not initialized"
        }

    return {
        "status": "configured",
        "webhook_path": "/telegram/webhook"
    }
