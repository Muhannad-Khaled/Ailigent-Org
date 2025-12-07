"""
Contract Routes

REST API endpoints for contract operations.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import logging

from src.integrations.odoo.client import get_odoo_client
from src.integrations.odoo.models.contracts import ContractOperations

router = APIRouter(prefix="/api/v1/contracts", tags=["Contracts"])
logger = logging.getLogger(__name__)


class ContractCreate(BaseModel):
    """Contract creation request."""
    name: str
    partner_id: int
    date_start: str
    date_end: Optional[str] = None
    recurring_interval: int = 1
    recurring_rule_type: str = "monthly"


class ContractUpdate(BaseModel):
    """Contract update request."""
    name: Optional[str] = None
    date_end: Optional[str] = None
    state: Optional[str] = None


def get_contract_ops() -> ContractOperations:
    """Get contract operations instance."""
    return ContractOperations(get_odoo_client())


@router.get("")
async def list_contracts(
    partner_name: Optional[str] = Query(None, description="Filter by partner name"),
    state: Optional[str] = Query(None, description="Filter by state"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results")
):
    """List contracts with optional filters."""
    try:
        ops = get_contract_ops()
        contracts = ops.search_contracts(
            partner_name=partner_name,
            state=state,
            limit=limit
        )
        return {"contracts": contracts, "count": len(contracts)}
    except Exception as e:
        logger.error(f"Error listing contracts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/expiring")
async def get_expiring_contracts(
    days: int = Query(30, ge=1, le=365, description="Days to look ahead")
):
    """Get contracts expiring within the specified number of days."""
    try:
        ops = get_contract_ops()
        contracts = ops.get_expiring_contracts(days=days)
        result = {
            "contracts": contracts,
            "count": len(contracts),
            "model": ops.contract_model,
            "supports_expiry": ops._has_date_fields()
        }
        if not ops._has_date_fields():
            result["message"] = f"The {ops.contract_model} model doesn't support expiration tracking"
        return result
    except Exception as e:
        logger.error(f"Error getting expiring contracts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_contract_summary():
    """Get contract summary statistics."""
    try:
        ops = get_contract_ops()
        summary = ops.get_contract_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{contract_id}")
async def get_contract(contract_id: int):
    """Get detailed information about a specific contract."""
    try:
        ops = get_contract_ops()
        contract = ops.get_contract_details(contract_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        return contract
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting contract {contract_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_contract(contract: ContractCreate):
    """Create a new contract."""
    try:
        ops = get_contract_ops()
        result = ops.create_contract(
            name=contract.name,
            partner_id=contract.partner_id,
            date_start=contract.date_start,
            date_end=contract.date_end,
            recurring_interval=contract.recurring_interval,
            recurring_rule_type=contract.recurring_rule_type
        )
        return {"success": True, "contract": result}
    except Exception as e:
        logger.error(f"Error creating contract: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{contract_id}")
async def update_contract(contract_id: int, contract: ContractUpdate):
    """Update an existing contract."""
    try:
        ops = get_contract_ops()

        # Build updates dict from non-None values
        updates = {}
        if contract.name is not None:
            updates["name"] = contract.name
        if contract.date_end is not None:
            updates["date_end"] = contract.date_end
        if contract.state is not None:
            updates["state"] = contract.state

        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")

        success = ops.update_contract(contract_id, updates)
        return {"success": success}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating contract {contract_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
