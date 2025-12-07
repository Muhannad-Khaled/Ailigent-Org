"""
HR Routes

REST API endpoints for HR operations.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import logging

from src.integrations.odoo.client import get_odoo_client
from src.integrations.odoo.models.hr import HROperations

router = APIRouter(prefix="/api/v1", tags=["HR"])
logger = logging.getLogger(__name__)


class LeaveRequest(BaseModel):
    """Leave request creation model."""
    employee_id: int
    leave_type_id: int
    date_from: str
    date_to: str
    description: Optional[str] = None


def get_hr_ops() -> HROperations:
    """Get HR operations instance."""
    return HROperations(get_odoo_client())


# ==================== Employee Endpoints ====================

@router.get("/employees")
async def list_employees(
    department: Optional[str] = Query(None, description="Filter by department"),
    job_title: Optional[str] = Query(None, description="Filter by job title"),
    limit: int = Query(50, ge=1, le=200)
):
    """List employees with optional filters."""
    try:
        ops = get_hr_ops()
        employees = ops.search_employees(
            department=department,
            job_title=job_title,
            limit=limit
        )
        return {"employees": employees, "count": len(employees)}
    except Exception as e:
        logger.error(f"Error listing employees: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employees/{employee_id}")
async def get_employee(employee_id: int):
    """Get detailed information about a specific employee."""
    try:
        ops = get_hr_ops()
        employee = ops.get_employee_details(employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        return employee
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting employee {employee_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Leave Endpoints ====================

@router.get("/leaves")
async def list_leaves(
    state: Optional[str] = Query(None, description="Filter by state"),
    department_id: Optional[int] = Query(None, description="Filter by department")
):
    """List leave requests."""
    try:
        ops = get_hr_ops()
        leaves = ops.get_pending_leave_requests(department_id=department_id)

        if state:
            leaves = [l for l in leaves if l.get("state") == state]

        return {"leaves": leaves, "count": len(leaves)}
    except Exception as e:
        logger.error(f"Error listing leaves: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/leaves")
async def create_leave(request: LeaveRequest):
    """Create a new leave request."""
    try:
        ops = get_hr_ops()
        result = ops.create_leave_request(
            employee_id=request.employee_id,
            leave_type_id=request.leave_type_id,
            date_from=request.date_from,
            date_to=request.date_to,
            description=request.description
        )
        return {"success": True, "leave": result}
    except Exception as e:
        logger.error(f"Error creating leave request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/leaves/{leave_id}/approve")
async def approve_leave(leave_id: int):
    """Approve a leave request."""
    try:
        ops = get_hr_ops()
        success = ops.approve_leave_request(leave_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"Error approving leave {leave_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/leaves/{leave_id}/reject")
async def reject_leave(leave_id: int, reason: Optional[str] = None):
    """Reject a leave request."""
    try:
        ops = get_hr_ops()
        success = ops.reject_leave_request(leave_id, reason=reason)
        return {"success": success}
    except Exception as e:
        logger.error(f"Error rejecting leave {leave_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leave-types")
async def get_leave_types():
    """Get available leave types."""
    try:
        ops = get_hr_ops()
        types = ops.get_leave_types()
        return {"leave_types": types}
    except Exception as e:
        logger.error(f"Error getting leave types: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employees/{employee_id}/leave-balance")
async def get_leave_balance(employee_id: int):
    """Get leave balance for an employee."""
    try:
        ops = get_hr_ops()
        balance = ops.get_leave_balance(employee_id)
        return balance
    except Exception as e:
        logger.error(f"Error getting leave balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Department Endpoints ====================

@router.get("/departments")
async def list_departments():
    """List all departments."""
    try:
        ops = get_hr_ops()
        departments = ops.get_departments()
        return {"departments": departments, "count": len(departments)}
    except Exception as e:
        logger.error(f"Error listing departments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/departments/{department_id}/org-chart")
async def get_department_org_chart(department_id: int):
    """Get organizational chart for a department."""
    try:
        ops = get_hr_ops()
        org_chart = ops.get_department_org_chart(department_id)
        return org_chart
    except Exception as e:
        logger.error(f"Error getting org chart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Recruitment Endpoints ====================

@router.get("/applicants")
async def list_applicants(
    job_id: Optional[int] = Query(None, description="Filter by job"),
    stage: Optional[str] = Query(None, description="Filter by stage"),
    limit: int = Query(50, ge=1, le=200)
):
    """List job applicants."""
    try:
        ops = get_hr_ops()
        applicants = ops.search_applicants(
            job_id=job_id,
            stage=stage,
            limit=limit
        )
        return {"applicants": applicants, "count": len(applicants)}
    except Exception as e:
        logger.error(f"Error listing applicants: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def list_jobs(published_only: bool = Query(True)):
    """List job positions."""
    try:
        ops = get_hr_ops()
        jobs = ops.get_job_positions(published_only=published_only)
        return {"jobs": jobs, "count": len(jobs)}
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Attendance Endpoints ====================

@router.get("/employees/{employee_id}/attendance")
async def get_attendance(
    employee_id: int,
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)")
):
    """Get attendance summary for an employee."""
    try:
        ops = get_hr_ops()
        summary = ops.get_attendance_summary(
            employee_id=employee_id,
            date_from=date_from,
            date_to=date_to
        )
        return summary
    except Exception as e:
        logger.error(f"Error getting attendance: {e}")
        raise HTTPException(status_code=500, detail=str(e))
