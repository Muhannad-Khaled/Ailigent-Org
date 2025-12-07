"""
Contracts Agent Tools

Tools for contract lifecycle management integrated with Odoo ERP.
"""

from typing import Dict, Any, List, Optional
from datetime import date, datetime
import logging

from langchain_core.tools import tool

from src.integrations.odoo.client import get_odoo_client
from src.integrations.odoo.models.contracts import ContractOperations

logger = logging.getLogger(__name__)


def _get_contract_ops() -> ContractOperations:
    """Get contract operations instance."""
    return ContractOperations(get_odoo_client())


@tool
def search_contracts(
    partner_name: Optional[str] = None,
    state: Optional[str] = None,
    expiring_within_days: Optional[int] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search contracts in Odoo ERP based on criteria.

    Args:
        partner_name: Filter by customer/vendor name (partial match)
        state: Filter by contract state (draft, open, close, cancelled)
        expiring_within_days: Find contracts expiring within N days from today
        limit: Maximum number of records to return (default 20)

    Returns:
        List of matching contracts with key details
    """
    try:
        ops = _get_contract_ops()
        contracts = ops.search_contracts(
            partner_name=partner_name,
            state=state,
            expiring_within_days=expiring_within_days,
            limit=limit
        )

        formatted = []
        for c in contracts:
            formatted.append({
                "id": c.get('id'),
                "name": c.get('name'),
                "partner": c.get('partner_id', [None, 'Unknown'])[1] if c.get('partner_id') else 'Unknown',
                "start_date": c.get('date_start'),
                "end_date": c.get('date_end'),
                "state": c.get('state'),
            })

        return formatted

    except Exception as e:
        logger.error(f"Error searching contracts: {e}")
        return [{"error": str(e)}]


@tool
def get_contract_details(contract_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific contract.

    Args:
        contract_id: The Odoo contract record ID

    Returns:
        Complete contract details
    """
    try:
        ops = _get_contract_ops()
        contract = ops.get_contract_details(contract_id)

        if not contract:
            return {"error": f"Contract with ID {contract_id} not found"}

        result = {
            "id": contract.get('id'),
            "name": contract.get('name'),
            "partner": contract.get('partner_id', [None, 'Unknown'])[1] if contract.get('partner_id') else 'Unknown',
            "partner_id": contract.get('partner_id', [None])[0] if contract.get('partner_id') else None,
            "state": contract.get('state'),
            "start_date": contract.get('date_start'),
            "end_date": contract.get('date_end'),
        }

        if contract.get('recurring_next_date'):
            result["recurring"] = {
                "next_date": contract.get('recurring_next_date'),
                "interval": contract.get('recurring_interval'),
                "rule_type": contract.get('recurring_rule_type')
            }

        return result

    except Exception as e:
        logger.error(f"Error getting contract details: {e}")
        return {"error": str(e)}


@tool
def get_expiring_contracts(days: int = 30) -> List[Dict[str, Any]]:
    """
    Get contracts expiring within the specified number of days.

    Args:
        days: Number of days to look ahead (default 30)

    Returns:
        List of expiring contracts with urgency levels
    """
    try:
        ops = _get_contract_ops()
        contracts = ops.get_expiring_contracts(days=days)

        today = date.today()
        formatted = []

        for c in contracts:
            end_date_str = c.get('date_end')
            if end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                days_until = (end_date - today).days

                if days_until <= 7:
                    urgency = "CRITICAL"
                elif days_until <= 14:
                    urgency = "URGENT"
                else:
                    urgency = "WARNING"
            else:
                days_until = None
                urgency = "UNKNOWN"

            formatted.append({
                "id": c.get('id'),
                "name": c.get('name'),
                "partner": c.get('partner_id', [None, 'Unknown'])[1] if c.get('partner_id') else 'Unknown',
                "end_date": end_date_str,
                "days_until_expiry": days_until,
                "urgency": urgency
            })

        formatted.sort(key=lambda x: x.get('days_until_expiry') or 999)
        return formatted

    except Exception as e:
        logger.error(f"Error getting expiring contracts: {e}")
        return [{"error": str(e)}]


@tool
def generate_contract_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a contract summary report.

    Args:
        date_from: Optional start date for report period (YYYY-MM-DD)
        date_to: Optional end date for report period (YYYY-MM-DD)

    Returns:
        Summary statistics
    """
    try:
        ops = _get_contract_ops()
        summary = ops.get_contract_summary(date_from=date_from, date_to=date_to)

        return {
            "report_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "period": {
                "from": date_from or "All time",
                "to": date_to or "Present"
            },
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return {"error": str(e)}


@tool
def search_partners(
    name: Optional[str] = None,
    is_company: bool = True,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for partners (customers/vendors) to use in contracts.

    Args:
        name: Partner name to search for (partial match)
        is_company: Filter for companies only (default True)
        limit: Maximum results to return

    Returns:
        List of matching partners with their IDs
    """
    try:
        client = get_odoo_client()

        domain = []
        if name:
            domain.append(['name', 'ilike', name])
        if is_company:
            domain.append(['is_company', '=', True])

        partners = client.search_read(
            'res.partner',
            domain,
            fields=['id', 'name', 'email', 'phone', 'city', 'country_id'],
            limit=limit,
            order='name asc'
        )

        return [
            {
                "id": p['id'],
                "name": p['name'],
                "email": p.get('email') or 'N/A',
                "phone": p.get('phone') or 'N/A',
                "location": f"{p.get('city') or ''}, {p['country_id'][1] if p.get('country_id') else 'N/A'}"
            }
            for p in partners
        ]

    except Exception as e:
        logger.error(f"Error searching partners: {e}")
        return [{"error": str(e)}]


# Export all tools as a list
contracts_tools = [
    search_contracts,
    get_contract_details,
    get_expiring_contracts,
    generate_contract_report,
    search_partners
]
