"""
Custom Exceptions

Centralized exception definitions for the multi-agent system.
"""

from typing import Optional, Dict, Any


class AgentSystemError(Exception):
    """Base exception for the agent system."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code or "AGENT_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details
        }


class OdooConnectionError(AgentSystemError):
    """Raised when connection to Odoo fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="ODOO_CONNECTION_ERROR",
            details=details
        )


class OdooOperationError(AgentSystemError):
    """Raised when an Odoo operation fails."""

    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        method: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        _details = details or {}
        if model:
            _details["model"] = model
        if method:
            _details["method"] = method
        super().__init__(
            message=message,
            code="ODOO_OPERATION_ERROR",
            details=_details
        )


class TelegramError(AgentSystemError):
    """Raised when a Telegram operation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="TELEGRAM_ERROR",
            details=details
        )


class AuthenticationError(AgentSystemError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR"
        )


class AgentRoutingError(AgentSystemError):
    """Raised when agent routing fails."""

    def __init__(self, message: str, agent: Optional[str] = None):
        super().__init__(
            message=message,
            code="AGENT_ROUTING_ERROR",
            details={"agent": agent} if agent else {}
        )


class ValidationError(AgentSystemError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field} if field else {}
        )
