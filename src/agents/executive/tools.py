"""
Executive Agent Tools

Tools available to the Executive Agent for system management and coordination.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from langchain_core.tools import tool

from src.integrations.odoo.client import get_odoo_client
from src.core.security import generate_thread_id

logger = logging.getLogger(__name__)


@tool
def get_user_context(user_id: str) -> Dict[str, Any]:
    """
    Retrieve user context including role, permissions, and recent interactions.

    Args:
        user_id: The unique identifier of the user (can be Telegram ID or internal ID)

    Returns:
        Dictionary containing user context information including:
        - user_id: The user identifier
        - role: User's role in the system
        - permissions: List of permitted operations
        - odoo_employee_id: Linked Odoo employee ID if available
    """
    try:
        client = get_odoo_client()

        # Try to find user in Odoo by email or name
        # This is a simplified lookup - in production, you'd have a user mapping table
        context = {
            "user_id": user_id,
            "role": "user",
            "permissions": ["read", "create"],
            "odoo_employee_id": None,
            "department": None
        }

        # Try to find corresponding employee
        employees = client.search_read(
            'hr.employee',
            [['work_email', 'ilike', user_id]],
            fields=['id', 'name', 'department_id', 'job_id'],
            limit=1
        )

        if employees:
            emp = employees[0]
            context["odoo_employee_id"] = emp['id']
            context["employee_name"] = emp['name']
            if emp.get('department_id'):
                context["department"] = emp['department_id'][1]
            if emp.get('job_id'):
                context["job_title"] = emp['job_id'][1]

        return context

    except Exception as e:
        logger.error(f"Error getting user context: {e}")
        return {
            "user_id": user_id,
            "role": "user",
            "permissions": ["read"],
            "error": str(e)
        }


@tool
def get_system_alerts() -> List[Dict[str, Any]]:
    """
    Retrieve current system alerts and important notifications.

    Returns:
        List of active alerts requiring attention, including:
        - Expiring contracts (within 30 days)
        - Pending leave requests
        - Important deadlines
    """
    alerts = []

    try:
        client = get_odoo_client()

        # Check for expiring contracts
        from src.integrations.odoo.models.contracts import ContractOperations
        contract_ops = ContractOperations(client)

        expiring = contract_ops.get_expiring_contracts(days=30)
        if expiring:
            alerts.append({
                "type": "contract_expiring",
                "severity": "warning",
                "message": f"{len(expiring)} contract(s) expiring in the next 30 days",
                "count": len(expiring),
                "items": [{"id": c['id'], "name": c['name']} for c in expiring[:5]]
            })

        # Check for pending leave requests
        from src.integrations.odoo.models.hr import HROperations
        hr_ops = HROperations(client)

        pending_leaves = hr_ops.get_pending_leave_requests()
        if pending_leaves:
            alerts.append({
                "type": "pending_leaves",
                "severity": "info",
                "message": f"{len(pending_leaves)} leave request(s) pending approval",
                "count": len(pending_leaves)
            })

    except Exception as e:
        logger.error(f"Error getting system alerts: {e}")
        alerts.append({
            "type": "system_error",
            "severity": "error",
            "message": f"Error checking alerts: {str(e)}"
        })

    return alerts


@tool
def log_interaction(
    user_id: str,
    agent: str,
    query: str,
    response: str,
    success: bool = True
) -> Dict[str, Any]:
    """
    Log an interaction for analytics and auditing purposes.

    Args:
        user_id: User identifier
        agent: Name of the agent that handled the request
        query: Original user query
        response: Agent response (summary)
        success: Whether the interaction was successful

    Returns:
        Confirmation of logged interaction with timestamp
    """
    timestamp = datetime.utcnow().isoformat()

    log_entry = {
        "timestamp": timestamp,
        "user_id": user_id,
        "agent": agent,
        "query_preview": query[:100] + "..." if len(query) > 100 else query,
        "response_preview": response[:100] + "..." if len(response) > 100 else response,
        "success": success
    }

    logger.info(f"Interaction logged: {log_entry}")

    return {
        "logged": True,
        "timestamp": timestamp,
        "interaction_id": generate_thread_id()[:8]
    }


@tool
def get_system_status() -> Dict[str, Any]:
    """
    Get the current status of all system components.

    Returns:
        Status information for all agents and integrations including:
        - Agent availability
        - Odoo connection status
        - System health metrics
    """
    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "agents": {
            "executive": {"status": "active", "health": "ok"},
            "contracts": {"status": "active", "health": "ok"},
            "hr": {"status": "active", "health": "ok"}
        },
        "integrations": {}
    }

    # Check Odoo connection
    try:
        client = get_odoo_client()
        version = client.get_version()
        status["integrations"]["odoo"] = {
            "status": "connected",
            "version": version.get("server_version", "unknown"),
            "health": "ok"
        }
    except Exception as e:
        status["integrations"]["odoo"] = {
            "status": "error",
            "error": str(e),
            "health": "critical"
        }

    return status


# Export all tools as a list for easy importing
executive_tools = [
    get_user_context,
    get_system_alerts,
    log_interaction,
    get_system_status
]
