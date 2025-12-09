"""
Finance Routes

REST API endpoints for finance and accounting operations.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import logging

from src.integrations.odoo.client import get_odoo_client
from src.integrations.odoo.models.finance import FinanceOperations

router = APIRouter(prefix="/api/v1/finance", tags=["Finance"])
logger = logging.getLogger(__name__)


# ==================== Request/Response Models ====================

class JournalEntryLine(BaseModel):
    """Journal entry line item."""
    account_id: int
    debit: float = 0
    credit: float = 0
    name: Optional[str] = None
    partner_id: Optional[int] = None


class JournalEntryCreate(BaseModel):
    """Journal entry creation request."""
    journal_id: int
    date: str
    reference: str
    lines: List[JournalEntryLine]
    auto_post: bool = False


# ==================== Helper Functions ====================

def get_finance_ops() -> FinanceOperations:
    """Get finance operations instance."""
    return FinanceOperations(get_odoo_client())


# ==================== Summary Endpoints ====================

@router.get("/summary")
async def get_financial_summary():
    """
    Get comprehensive financial summary.

    Returns total receivables, payables, cash balance, and overdue info.
    """
    try:
        ops = get_finance_ops()
        summary = ops.get_financial_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting financial summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_all_alerts(
    overdue_threshold: int = Query(30, description="Days overdue for high priority"),
    cash_threshold: float = Query(10000, description="Low cash balance threshold"),
    transaction_threshold: float = Query(50000, description="Large transaction threshold")
):
    """
    Get all financial alerts.

    Includes overdue invoices, low cash warnings, and large transactions.
    """
    try:
        ops = get_finance_ops()
        alerts = ops.get_all_alerts(
            overdue_threshold=overdue_threshold,
            cash_threshold=cash_threshold,
            transaction_threshold=transaction_threshold
        )

        # Calculate total
        alerts['total_alerts'] = (
            len(alerts.get('overdue_invoices', [])) +
            len(alerts.get('cash_flow', [])) +
            len(alerts.get('large_transactions', []))
        )

        return alerts
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Invoice Endpoints ====================

@router.get("/invoices")
async def list_invoices(
    partner_name: Optional[str] = Query(None, description="Filter by partner name"),
    state: Optional[str] = Query(None, description="Filter by state (draft, posted, cancel)"),
    move_type: Optional[str] = Query(None, description="Filter by type (out_invoice, in_invoice)"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    payment_state: Optional[str] = Query(None, description="Filter by payment state"),
    limit: int = Query(50, ge=1, le=200)
):
    """List invoices with optional filters."""
    try:
        ops = get_finance_ops()
        invoices = ops.search_invoices(
            partner_name=partner_name,
            state=state,
            move_type=move_type,
            date_from=date_from,
            date_to=date_to,
            payment_state=payment_state,
            limit=limit
        )
        return {"invoices": invoices, "count": len(invoices)}
    except Exception as e:
        logger.error(f"Error listing invoices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices/outstanding")
async def get_outstanding_invoices(
    days_overdue: int = Query(0, description="Minimum days overdue (0 = all unpaid)")
):
    """Get unpaid or overdue invoices."""
    try:
        ops = get_finance_ops()
        invoices = ops.get_outstanding_invoices(days_overdue=days_overdue)

        total_amount = sum(inv.get('amount_residual', 0) for inv in invoices)

        return {
            "invoices": invoices,
            "count": len(invoices),
            "total_outstanding": total_amount
        }
    except Exception as e:
        logger.error(f"Error getting outstanding invoices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: int):
    """Get detailed invoice information."""
    try:
        ops = get_finance_ops()
        invoice = ops.get_invoice_details(invoice_id)

        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        return invoice
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invoice {invoice_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Payment Endpoints ====================

@router.get("/payments")
async def list_payments(
    partner_name: Optional[str] = Query(None, description="Filter by partner name"),
    payment_type: Optional[str] = Query(None, description="Filter by type (inbound, outbound)"),
    date_from: Optional[str] = Query(None, description="Filter from date"),
    date_to: Optional[str] = Query(None, description="Filter to date"),
    limit: int = Query(50, ge=1, le=200)
):
    """List payment records with optional filters."""
    try:
        ops = get_finance_ops()
        payments = ops.search_payments(
            partner_name=partner_name,
            payment_type=payment_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit
        )
        return {"payments": payments, "count": len(payments)}
    except Exception as e:
        logger.error(f"Error listing payments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/{payment_id}")
async def get_payment(payment_id: int):
    """Get detailed payment information."""
    try:
        ops = get_finance_ops()
        payment = ops.get_payment_details(payment_id)

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        return payment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting payment {payment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Report Endpoints ====================

@router.get("/reports/profit-loss")
async def get_profit_loss_report(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get Profit & Loss report."""
    try:
        ops = get_finance_ops()
        report = ops.get_profit_loss(date_from=date_from, date_to=date_to)
        return report
    except Exception as e:
        logger.error(f"Error getting P&L report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/cash-flow")
async def get_cash_flow_report(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get cash flow report."""
    try:
        ops = get_finance_ops()
        report = ops.get_cash_flow(date_from=date_from, date_to=date_to)
        return report
    except Exception as e:
        logger.error(f"Error getting cash flow report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/expenses")
async def get_expense_report(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get expense breakdown report."""
    try:
        ops = get_finance_ops()
        report = ops.get_expense_breakdown(date_from=date_from, date_to=date_to)
        return report
    except Exception as e:
        logger.error(f"Error getting expense report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/revenue")
async def get_revenue_report(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get revenue breakdown report."""
    try:
        ops = get_finance_ops()
        report = ops.get_revenue_breakdown(date_from=date_from, date_to=date_to)
        return report
    except Exception as e:
        logger.error(f"Error getting revenue report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Journal Endpoints ====================

@router.get("/journals")
async def list_journals(
    journal_type: Optional[str] = Query(None, description="Filter by type (sale, purchase, cash, bank, general)")
):
    """List accounting journals."""
    try:
        ops = get_finance_ops()
        journals = ops.get_journals(journal_type=journal_type)
        return {"journals": journals, "count": len(journals)}
    except Exception as e:
        logger.error(f"Error listing journals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/journal-entries")
async def list_journal_entries(
    journal_id: Optional[int] = Query(None, description="Filter by journal ID"),
    date_from: Optional[str] = Query(None, description="Filter from date"),
    date_to: Optional[str] = Query(None, description="Filter to date"),
    limit: int = Query(50, ge=1, le=200)
):
    """List journal entries."""
    try:
        ops = get_finance_ops()
        entries = ops.search_journal_entries(
            journal_id=journal_id,
            date_from=date_from,
            date_to=date_to,
            limit=limit
        )
        return {"entries": entries, "count": len(entries)}
    except Exception as e:
        logger.error(f"Error listing journal entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/journal-entries")
async def create_journal_entry(entry: JournalEntryCreate):
    """
    Create a new journal entry.

    Entry must be balanced (total debits = total credits).
    """
    try:
        ops = get_finance_ops()

        # Convert Pydantic models to dicts
        lines = [
            {
                "account_id": line.account_id,
                "debit": line.debit,
                "credit": line.credit,
                "name": line.name,
                "partner_id": line.partner_id
            }
            for line in entry.lines
        ]

        result = ops.create_journal_entry(
            journal_id=entry.journal_id,
            date=entry.date,
            ref=entry.reference,
            lines=lines,
            auto_post=entry.auto_post
        )

        if result.get('error'):
            raise HTTPException(status_code=400, detail=result['error'])

        return {"success": True, "entry": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating journal entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))
