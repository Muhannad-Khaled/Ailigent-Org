"""
HR Agent Tools

Tools for human resources operations integrated with Odoo ERP.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from langchain_core.tools import tool

from src.integrations.odoo.client import get_odoo_client
from src.integrations.odoo.models.hr import HROperations

logger = logging.getLogger(__name__)


def _get_hr_ops() -> HROperations:
    """Get HR operations instance."""
    return HROperations(get_odoo_client())


@tool
def search_employees(
    department: Optional[str] = None,
    job_title: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search employees in Odoo based on criteria.

    Args:
        department: Filter by department name (partial match)
        job_title: Filter by job title (partial match)
        limit: Maximum results to return (default 20)

    Returns:
        List of matching employees with key details
    """
    try:
        ops = _get_hr_ops()
        employees = ops.search_employees(
            department=department,
            job_title=job_title,
            limit=limit
        )

        return [
            {
                "id": e.get('id'),
                "name": e.get('name'),
                "email": e.get('work_email'),
                "phone": e.get('work_phone'),
                "department": e.get('department_id', [None, 'N/A'])[1] if e.get('department_id') else 'N/A',
                "job_title": e.get('job_id', [None, 'N/A'])[1] if e.get('job_id') else 'N/A',
            }
            for e in employees
        ]

    except Exception as e:
        logger.error(f"Error searching employees: {e}")
        return [{"error": str(e)}]


@tool
def get_employee_details(employee_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific employee.

    Args:
        employee_id: The Odoo employee record ID

    Returns:
        Complete employee details
    """
    try:
        ops = _get_hr_ops()
        employee = ops.get_employee_details(employee_id)

        if not employee:
            return {"error": f"Employee with ID {employee_id} not found"}

        result = {
            "id": employee.get('id'),
            "name": employee.get('name'),
            "work_email": employee.get('work_email'),
            "work_phone": employee.get('work_phone'),
            "mobile": employee.get('mobile_phone'),
            "department": employee.get('department_id', [None, 'N/A'])[1] if employee.get('department_id') else 'N/A',
            "job_title": employee.get('job_id', [None, 'N/A'])[1] if employee.get('job_id') else 'N/A',
            "manager": employee.get('parent_id', [None, 'N/A'])[1] if employee.get('parent_id') else 'N/A',
        }

        return result

    except Exception as e:
        logger.error(f"Error getting employee details: {e}")
        return {"error": str(e)}


@tool
def get_pending_leave_requests(
    department_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get pending leave requests awaiting approval.

    Args:
        department_id: Filter by department

    Returns:
        List of pending leave requests with details
    """
    try:
        ops = _get_hr_ops()
        requests = ops.get_pending_leave_requests(department_id=department_id)

        return [
            {
                "id": r.get('id'),
                "employee": r.get('employee_id', [None, 'Unknown'])[1] if r.get('employee_id') else 'Unknown',
                "leave_type": r.get('holiday_status_id', [None, 'Unknown'])[1] if r.get('holiday_status_id') else 'Unknown',
                "date_from": r.get('date_from'),
                "date_to": r.get('date_to'),
                "days": r.get('number_of_days'),
                "state": r.get('state')
            }
            for r in requests
        ]

    except Exception as e:
        logger.error(f"Error getting pending leave requests: {e}")
        return [{"error": str(e)}]


@tool
def get_leave_types() -> List[Dict[str, Any]]:
    """
    Get available leave types (vacation, sick, etc.).

    Returns:
        List of leave types with their IDs and names
    """
    try:
        ops = _get_hr_ops()
        types = ops.get_leave_types()

        return [
            {
                "id": t.get('id'),
                "name": t.get('name'),
            }
            for t in types
        ]

    except Exception as e:
        logger.error(f"Error getting leave types: {e}")
        return [{"error": str(e)}]


@tool
def get_departments() -> List[Dict[str, Any]]:
    """
    Get all departments in the organization.

    Returns:
        List of departments with their details
    """
    try:
        ops = _get_hr_ops()
        departments = ops.get_departments()

        return [
            {
                "id": d.get('id'),
                "name": d.get('name'),
                "manager": d.get('manager_id', [None, 'N/A'])[1] if d.get('manager_id') else 'N/A'
            }
            for d in departments
        ]

    except Exception as e:
        logger.error(f"Error getting departments: {e}")
        return [{"error": str(e)}]


@tool
def get_job_positions() -> List[Dict[str, Any]]:
    """
    Get available job positions.

    Returns:
        List of job positions with details
    """
    try:
        ops = _get_hr_ops()
        jobs = ops.get_job_positions()

        return [
            {
                "id": j.get('id'),
                "name": j.get('name'),
                "department": j.get('department_id', [None, 'N/A'])[1] if j.get('department_id') else 'N/A',
            }
            for j in jobs
        ]

    except Exception as e:
        logger.error(f"Error getting job positions: {e}")
        return [{"error": str(e)}]


# Export all tools as a list
hr_tools = [
    search_employees,
    get_employee_details,
    get_pending_leave_requests,
    get_leave_types,
    get_departments,
    get_job_positions,
]
