"""
Google Gemini LLM Configuration

Provides configured Gemini model instances for the agent system.
"""

from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config import settings


def create_gemini_model(
    model: Optional[str] = None,
    temperature: float = 0.1
) -> ChatGoogleGenerativeAI:
    """
    Create a configured Gemini model instance.

    Args:
        model: Model name (uses settings default if not provided)
        temperature: Model temperature (0.0 to 1.0)

    Returns:
        Configured ChatGoogleGenerativeAI instance
    """
    return ChatGoogleGenerativeAI(
        model=model or settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=temperature,
        convert_system_message_to_human=True
    )


# Singleton instance for default model
_default_model: Optional[ChatGoogleGenerativeAI] = None


def get_gemini_model() -> ChatGoogleGenerativeAI:
    """
    Get or create singleton Gemini model instance.

    Returns:
        Default configured Gemini model
    """
    global _default_model
    if _default_model is None:
        _default_model = create_gemini_model()
    return _default_model
