"""Request schemas for API endpoints."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., min_length=1, max_length=4000)
    user_id: Optional[str] = "anonymous"
    thread_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ContractCreateRequest(BaseModel):
    """Contract creation request."""
    name: str = Field(..., min_length=1, max_length=255)
    partner_id: int = Field(..., gt=0)
    date_start: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_end: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    recurring_interval: int = Field(default=1, ge=1)
    recurring_rule_type: str = Field(default="monthly")


class ContractUpdateRequest(BaseModel):
    """Contract update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    date_end: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    state: Optional[str] = None


class LeaveCreateRequest(BaseModel):
    """Leave request creation model."""
    employee_id: int = Field(..., gt=0)
    leave_type_id: int = Field(..., gt=0)
    date_from: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_to: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    description: Optional[str] = None


class EmployeeSearchRequest(BaseModel):
    """Employee search request."""
    department: Optional[str] = None
    job_title: Optional[str] = None
    manager_id: Optional[int] = None
    limit: int = Field(default=50, ge=1, le=200)
