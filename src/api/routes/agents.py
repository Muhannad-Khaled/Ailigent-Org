"""
Agent Interaction Routes

Endpoints for interacting with the multi-agent system.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

from src.agents.supervisor import invoke_agent, get_last_ai_message
from src.core.security import generate_thread_id

router = APIRouter(prefix="/api/v1", tags=["Agents"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    user_id: Optional[str] = "anonymous"
    thread_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    thread_id: str
    agent: str = "executive"


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Send a message to the agent system.

    The system will automatically route the message to the appropriate
    specialized agent (Contracts or HR) based on the content.
    """
    try:
        thread_id = request.thread_id or generate_thread_id()

        user_context = {
            "user_id": request.user_id,
        }

        result = await invoke_agent(
            message=request.message,
            thread_id=thread_id,
            user_context=user_context
        )

        response_text = get_last_ai_message(result)

        return ChatResponse(
            response=response_text,
            thread_id=thread_id,
            agent="executive"
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/status")
async def get_agent_status():
    """Get the status of all agents in the system."""
    return {
        "agents": {
            "executive": {
                "name": "Executive Agent",
                "role": "Orchestrator",
                "status": "active"
            },
            "contracts": {
                "name": "Contracts Agent",
                "role": "Contract Lifecycle Management",
                "status": "active"
            },
            "hr": {
                "name": "HR Agent",
                "role": "Human Resources Operations",
                "status": "active"
            }
        }
    }
