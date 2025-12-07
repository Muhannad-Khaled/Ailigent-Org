"""
HR Model Operations

Operations for Human Resources management in Odoo.
"""

from typing import Dict, List, Any, Optional
from datetime import date, datetime, timedelta
import logging

from src.integrations.odoo.client import OdooClient, get_odoo_client

logger = logging.getLogger(__name__)


class HROperations:
    """HR-related operations for Odoo."""

    def __init__(self, client: Optional[OdooClient] = None):
        """
        Initialize HR operations.

        Args:
            client: Optional Odoo client. Uses singleton if not provided.
        """
        self.client = client or get_odoo_client()

    # ==================== Employee Operations ====================

    def search_employees(
        self,
        department: Optional[str] = None,
        job_title: Optional[str] = None,
        manager_id: Optional[int] = None,
        active: bool = True,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search employees based on criteria.

        Args:
            department: Filter by department name
            job_title: Filter by job title
            manager_id: Filter by manager's employee ID
            active: Filter by active status
            limit: Maximum records

        Returns:
            List of matching employees
        """
        domain = [['active', '=', active]]

        if department:
            domain.append(['department_id.name', 'ilike', department])

        if job_title:
            domain.append(['job_id.name', 'ilike', job_title])

        if manager_id:
            domain.append(['parent_id', '=', manager_id])

        return self.client.search_read(
            'hr.employee',
            domain,
            fields=[
                'name', 'work_email', 'work_phone', 'mobile_phone',
                'department_id', 'job_id', 'parent_id', 'coach_id',
                'work_location_id', 'company_id'
            ],
            limit=limit,
            order='name asc'
        )

    def get_employee_details(self, employee_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific employee.

        Args:
            employee_id: Odoo employee record ID

        Returns:
            Complete employee details
        """
        employees = self.client.read('hr.employee', [employee_id])
        if not employees:
            return {}

        employee = employees[0]

        # Get current contract if available
        if self.client.check_model_exists('hr.contract'):
            contracts = self.client.search_read(
                'hr.contract',
                [
                    ['employee_id', '=', employee_id],
                    ['state', '=', 'open']
                ],
                fields=['name', 'wage', 'date_start', 'date_end', 'state'],
                limit=1
            )
            employee['current_contract'] = contracts[0] if contracts else None

        return employee

    def create_employee(
        self,
        name: str,
        job_id: int,
        department_id: int,
        work_email: str,
        manager_id: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new employee record.

        Args:
            name: Employee full name
            job_id: Job position ID
            department_id: Department ID
            work_email: Work email address
            manager_id: Optional manager's employee ID

        Returns:
            Created employee details
        """
        values = {
            'name': name,
            'job_id': job_id,
            'department_id': department_id,
            'work_email': work_email,
        }

        if manager_id:
            values['parent_id'] = manager_id

        values.update(kwargs)

        employee_id = self.client.create('hr.employee', values)

        return {
            'id': employee_id,
            'name': name,
            'job_id': job_id,
            'department_id': department_id,
            'work_email': work_email
        }

    # ==================== Leave Operations ====================

    def get_leave_types(self) -> List[Dict[str, Any]]:
        """Get available leave types."""
        return self.client.search_read(
            'hr.leave.type',
            [],
            fields=['name', 'request_unit', 'allocation_type'],
            order='name asc'
        )

    def get_leave_balance(self, employee_id: int) -> Dict[str, Any]:
        """
        Get leave balance for an employee by leave type.

        Args:
            employee_id: Employee ID

        Returns:
            Dictionary of leave types and remaining days
        """
        # Get allocations
        allocations = self.client.search_read(
            'hr.leave.allocation',
            [
                ['employee_id', '=', employee_id],
                ['state', '=', 'validate']
            ],
            fields=['holiday_status_id', 'number_of_days', 'leaves_taken']
        )

        balance = {}
        for alloc in allocations:
            leave_type = alloc['holiday_status_id'][1] if alloc['holiday_status_id'] else 'Unknown'
            remaining = alloc['number_of_days'] - (alloc.get('leaves_taken', 0) or 0)
            balance[leave_type] = {
                'allocated': alloc['number_of_days'],
                'taken': alloc.get('leaves_taken', 0) or 0,
                'remaining': remaining
            }

        return balance

    def create_leave_request(
        self,
        employee_id: int,
        leave_type_id: int,
        date_from: str,
        date_to: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new leave request for an employee.

        Args:
            employee_id: Employee ID
            leave_type_id: Leave type ID
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            description: Optional reason/description

        Returns:
            Created leave request details
        """
        values = {
            'employee_id': employee_id,
            'holiday_status_id': leave_type_id,
            'date_from': f"{date_from} 08:00:00",
            'date_to': f"{date_to} 17:00:00",
            'request_date_from': date_from,
            'request_date_to': date_to,
        }

        if description:
            values['name'] = description

        leave_id = self.client.create('hr.leave', values)

        return {
            'id': leave_id,
            'employee_id': employee_id,
            'leave_type_id': leave_type_id,
            'date_from': date_from,
            'date_to': date_to,
            'state': 'draft'
        }

    def get_pending_leave_requests(
        self,
        manager_id: Optional[int] = None,
        department_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get pending leave requests awaiting approval.

        Args:
            manager_id: Filter by manager
            department_id: Filter by department

        Returns:
            List of pending leave requests
        """
        domain = [['state', 'in', ['draft', 'confirm']]]

        if manager_id:
            # Get employees reporting to this manager
            employees = self.client.search(
                'hr.employee',
                [['parent_id', '=', manager_id]]
            )
            if employees:
                domain.append(['employee_id', 'in', employees])

        if department_id:
            domain.append(['employee_id.department_id', '=', department_id])

        return self.client.search_read(
            'hr.leave',
            domain,
            fields=[
                'employee_id', 'holiday_status_id', 'date_from', 'date_to',
                'number_of_days', 'state', 'name'
            ],
            order='date_from asc'
        )

    def approve_leave_request(self, leave_id: int) -> bool:
        """
        Approve a pending leave request.

        Args:
            leave_id: Leave request ID

        Returns:
            Success status
        """
        try:
            self.client.call_method('hr.leave', 'action_validate', [leave_id])
            return True
        except Exception as e:
            logger.error(f"Failed to approve leave {leave_id}: {e}")
            return False

    def reject_leave_request(self, leave_id: int, reason: Optional[str] = None) -> bool:
        """
        Reject a leave request.

        Args:
            leave_id: Leave request ID
            reason: Optional rejection reason

        Returns:
            Success status
        """
        try:
            self.client.call_method('hr.leave', 'action_refuse', [leave_id])
            return True
        except Exception as e:
            logger.error(f"Failed to reject leave {leave_id}: {e}")
            return False

    # ==================== Recruitment Operations ====================

    def search_applicants(
        self,
        job_id: Optional[int] = None,
        stage: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search job applicants in recruitment pipeline.

        Args:
            job_id: Filter by job position
            stage: Filter by pipeline stage name

        Returns:
            List of matching applicants
        """
        domain = []

        if job_id:
            domain.append(['job_id', '=', job_id])

        if stage:
            domain.append(['stage_id.name', 'ilike', stage])

        return self.client.search_read(
            'hr.applicant',
            domain,
            fields=[
                'partner_name', 'email_from', 'partner_phone',
                'job_id', 'department_id', 'stage_id',
                'salary_expected', 'salary_proposed',
                'create_date', 'kanban_state'
            ],
            limit=limit,
            order='create_date desc'
        )

    def get_job_positions(self, published_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get available job positions.

        Args:
            published_only: Only return published positions

        Returns:
            List of job positions
        """
        domain = []
        if published_only:
            domain.append(['state', '=', 'recruit'])

        return self.client.search_read(
            'hr.job',
            domain,
            fields=[
                'name', 'department_id', 'no_of_recruitment',
                'no_of_employee', 'state', 'description'
            ],
            order='name asc'
        )

    # ==================== Attendance Operations ====================

    def get_attendance_summary(
        self,
        employee_id: int,
        date_from: str,
        date_to: str
    ) -> Dict[str, Any]:
        """
        Get attendance summary for an employee.

        Args:
            employee_id: Employee ID
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)

        Returns:
            Attendance summary
        """
        if not self.client.check_model_exists('hr.attendance'):
            return {'error': 'Attendance module not installed'}

        attendance = self.client.search_read(
            'hr.attendance',
            [
                ['employee_id', '=', employee_id],
                ['check_in', '>=', f"{date_from} 00:00:00"],
                ['check_in', '<=', f"{date_to} 23:59:59"]
            ],
            fields=['check_in', 'check_out', 'worked_hours'],
            order='check_in asc'
        )

        total_hours = sum(a.get('worked_hours', 0) or 0 for a in attendance)
        days_present = len(set(a['check_in'][:10] for a in attendance if a.get('check_in')))

        return {
            'employee_id': employee_id,
            'date_from': date_from,
            'date_to': date_to,
            'total_hours': round(total_hours, 2),
            'days_present': days_present,
            'records': attendance
        }

    # ==================== Department Operations ====================

    def get_departments(self) -> List[Dict[str, Any]]:
        """Get all departments."""
        return self.client.search_read(
            'hr.department',
            [],
            fields=['name', 'parent_id', 'manager_id', 'company_id'],
            order='name asc'
        )

    def get_department_org_chart(self, department_id: int) -> Dict[str, Any]:
        """
        Get organizational chart for a department.

        Args:
            department_id: Department ID

        Returns:
            Hierarchical org chart structure
        """
        # Get department info
        depts = self.client.read('hr.department', [department_id])
        if not depts:
            return {}

        dept = depts[0]

        # Get employees in department
        employees = self.client.search_read(
            'hr.employee',
            [['department_id', '=', department_id]],
            fields=['name', 'job_id', 'parent_id', 'work_email'],
            order='name asc'
        )

        # Build hierarchy
        def build_tree(parent_id: Optional[int] = None) -> List[Dict]:
            children = []
            for emp in employees:
                emp_parent = emp['parent_id'][0] if emp['parent_id'] else None
                if emp_parent == parent_id:
                    emp_data = {
                        'id': emp['id'],
                        'name': emp['name'],
                        'job': emp['job_id'][1] if emp['job_id'] else None,
                        'reports': build_tree(emp['id'])
                    }
                    children.append(emp_data)
            return children

        # Find the manager (top of hierarchy)
        manager_id = dept['manager_id'][0] if dept['manager_id'] else None

        return {
            'department': dept['name'],
            'manager_id': manager_id,
            'org_chart': build_tree(None) if not manager_id else build_tree(manager_id)
        }
