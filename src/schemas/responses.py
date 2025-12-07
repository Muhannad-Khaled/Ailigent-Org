"""Response schemas for API endpoints."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    thread_id: str
    agent: str = "executive"
    timestamp: datetime = None

    def __init__(self, **data):
        if data.get('timestamp') is None:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class AgentInfo(BaseModel):
    """Individual agent information."""
    name: str
    role: str
    status: str


class AgentStatusResponse(BaseModel):
    """Agent status response."""
    agents: Dict[str, AgentInfo]


class ComponentHealth(BaseModel):
    """Health status of a component."""
    status: str
    version: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str
    components: Optional[Dict[str, ComponentHealth]] = None


class ContractResponse(BaseModel):
    """Contract response model."""
    id: int
    name: str
    partner: str
    partner_id: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    state: Optional[str] = None


class ContractListResponse(BaseModel):
    """Contract list response."""
    contracts: List[ContractResponse]
    count: int


class EmployeeResponse(BaseModel):
    """Employee response model."""
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    manager: Optional[str] = None


class EmployeeListResponse(BaseModel):
    """Employee list response."""
    employees: List[EmployeeResponse]
    count: int


class LeaveResponse(BaseModel):
    """Leave request response."""
    id: int
    employee: str
    leave_type: str
    date_from: str
    date_to: str
    days: Optional[float] = None
    state: str


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
