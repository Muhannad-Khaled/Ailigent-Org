"""
Agent State Management

Defines shared state schemas for the multi-agent system.
State is passed between agents and persisted via checkpointer.
"""

from typing import TypedDict, List, Optional, Any, Annotated, Dict
from datetime import datetime
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class UserContext(TypedDict, total=False):
    """User context information."""
    user_id: str
    telegram_id: Optional[int]
    username: Optional[str]
    role: str
    department_id: Optional[int]
    employee_id: Optional[int]
    permissions: List[str]
    language: str


class TaskInfo(TypedDict, total=False):
    """Information about a task being processed."""
    task_id: str
    task_type: str
    description: str
    agent: str
    status: str
    created_at: str
    completed_at: Optional[str]
    result: Optional[str]


class PendingAction(TypedDict, total=False):
    """Action requiring user confirmation."""
    action_id: str
    action_type: str
    description: str
    data: Dict[str, Any]
    created_at: str
    expires_at: Optional[str]


class AgentState(TypedDict, total=False):
    """
    Shared state for the multi-agent system.

    This state is passed between agents and persisted via checkpointer.
    Uses add_messages reducer for message accumulation.
    """
    # Conversation messages with reducer for appending
    messages: Annotated[List[BaseMessage], add_messages]

    # User context
    user_context: Optional[UserContext]

    # Current active agent
    current_agent: str

    # Thread/conversation identifier
    thread_id: str

    # Task tracking
    current_task: Optional[TaskInfo]
    task_history: List[TaskInfo]

    # Odoo context (cached data from recent operations)
    odoo_cache: Dict[str, Any]

    # Pending actions requiring user confirmation
    pending_actions: List[PendingAction]

    # Error state
    last_error: Optional[str]

    # Metadata
    created_at: str
    updated_at: str


class ConversationSummary(TypedDict):
    """Long-term conversation summary for memory."""
    thread_id: str
    user_id: str
    summary: str
    key_entities: List[Dict[str, Any]]
    topics_discussed: List[str]
    created_at: str
    updated_at: str


def create_initial_state(
    thread_id: str,
    user_context: Optional[UserContext] = None
) -> AgentState:
    """
    Create initial agent state for a new conversation.

    Args:
        thread_id: Unique thread identifier
        user_context: Optional user context

    Returns:
        Initialized AgentState
    """
    now = datetime.utcnow().isoformat()

    return AgentState(
        messages=[],
        user_context=user_context,
        current_agent="executive_agent",
        thread_id=thread_id,
        current_task=None,
        task_history=[],
        odoo_cache={},
        pending_actions=[],
        last_error=None,
        created_at=now,
        updated_at=now
    )


def create_task_info(
    task_id: str,
    task_type: str,
    description: str,
    agent: str
) -> TaskInfo:
    """Create a new task info object."""
    return TaskInfo(
        task_id=task_id,
        task_type=task_type,
        description=description,
        agent=agent,
        status="pending",
        created_at=datetime.utcnow().isoformat(),
        completed_at=None,
        result=None
    )
