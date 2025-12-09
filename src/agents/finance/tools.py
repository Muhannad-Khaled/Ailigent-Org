"""
Finance Agent Tools

Tools for financial and accounting operations integrated with Odoo ERP.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from langchain_core.tools import tool

from src.integrations.odoo.client import get_odoo_client
from src.integrations.odoo.models.finance import FinanceOperations

logger = logging.getLogger(__name__)


def _get_finance_ops() -> FinanceOperations:
    """Get Finance operations instance."""
    return FinanceOperations(get_odoo_client())


# ==================== Summary Tools ====================

@tool
def get_financial_summary() -> Dict[str, Any]:
    """
    Get a comprehensive financial overview.

    Use this tool when the user asks about:
    - Overall financial status / health
    - How the company is doing financially
    - Quick financial summary or overview
    - Total receivables, payables, or cash balance

    Returns:
        Financial summary with receivables, payables, cash balance, and overdue info
    """
    try:
        ops = _get_finance_ops()
        summary = ops.get_financial_summary()

        return {
            "total_receivables": summary.get('total_receivables', 0),
            "total_payables": summary.get('total_payables', 0),
            "cash_balance": summary.get('cash_balance', 0),
            "overdue_invoices": {
                "count": summary.get('overdue_count', 0),
                "amount": summary.get('overdue_amount', 0)
            }
        }

    except Exception as e:
        logger.error(f"Error getting financial summary: {e}")
        return {"error": str(e)}


# ==================== Invoice Tools ====================

@tool
def search_invoices(
    partner_name: Optional[str] = None,
    state: Optional[str] = None,
    move_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search invoices in Odoo.

    Use this tool when the user wants to:
    - List or search invoices
    - Find invoices for a specific customer/vendor
    - See recent invoices
    - Filter invoices by status or date

    Args:
        partner_name: Filter by customer/vendor name (partial match)
        state: Filter by state - "draft", "posted", or "cancel"
        move_type: Filter by type - "out_invoice" (customer), "in_invoice" (vendor), "out_refund", "in_refund"
        date_from: Filter from date (YYYY-MM-DD)
        date_to: Filter to date (YYYY-MM-DD)
        limit: Maximum results to return (default 20)

    Returns:
        List of matching invoices with key details
    """
    try:
        ops = _get_finance_ops()
        invoices = ops.search_invoices(
            partner_name=partner_name,
            state=state,
            move_type=move_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit
        )

        return [
            {
                "id": inv.get('id'),
                "number": inv.get('name'),
                "partner": inv.get('partner_id', [None, 'N/A'])[1] if inv.get('partner_id') else 'N/A',
                "date": inv.get('invoice_date'),
                "due_date": inv.get('invoice_date_due'),
                "total": inv.get('amount_total', 0),
                "balance_due": inv.get('amount_residual', 0),
                "status": inv.get('state'),
                "payment_status": inv.get('payment_state'),
                "type": "Customer Invoice" if inv.get('move_type') == 'out_invoice' else
                        "Vendor Bill" if inv.get('move_type') == 'in_invoice' else
                        "Credit Note" if inv.get('move_type') in ['out_refund', 'in_refund'] else inv.get('move_type')
            }
            for inv in invoices
        ]

    except Exception as e:
        logger.error(f"Error searching invoices: {e}")
        return [{"error": str(e)}]


@tool
def get_invoice_details(invoice_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific invoice.

    Use this tool when the user wants:
    - Full details of a specific invoice
    - Invoice line items
    - Payment history for an invoice

    Args:
        invoice_id: The Odoo invoice record ID

    Returns:
        Complete invoice details including line items and payments
    """
    try:
        ops = _get_finance_ops()
        invoice = ops.get_invoice_details(invoice_id)

        if not invoice:
            return {"error": f"Invoice with ID {invoice_id} not found"}

        result = {
            "id": invoice.get('id'),
            "number": invoice.get('name'),
            "partner": invoice.get('partner_id', [None, 'N/A'])[1] if invoice.get('partner_id') else 'N/A',
            "date": invoice.get('invoice_date'),
            "due_date": invoice.get('invoice_date_due'),
            "total": invoice.get('amount_total', 0),
            "subtotal": invoice.get('amount_untaxed', 0),
            "tax": invoice.get('amount_tax', 0),
            "balance_due": invoice.get('amount_residual', 0),
            "status": invoice.get('state'),
            "payment_status": invoice.get('payment_state'),
            "reference": invoice.get('ref'),
            "lines": [
                {
                    "product": line.get('product_id', [None, line.get('name', 'N/A')])[1] if line.get('product_id') else line.get('name', 'N/A'),
                    "quantity": line.get('quantity', 0),
                    "unit_price": line.get('price_unit', 0),
                    "subtotal": line.get('price_subtotal', 0)
                }
                for line in invoice.get('invoice_lines', [])
            ],
            "payments": invoice.get('payments', [])
        }

        return result

    except Exception as e:
        logger.error(f"Error getting invoice details: {e}")
        return {"error": str(e)}


@tool
def get_outstanding_invoices(days_overdue: int = 0) -> List[Dict[str, Any]]:
    """
    Get unpaid or overdue invoices.

    Use this tool when the user asks about:
    - Overdue invoices
    - Unpaid invoices
    - Outstanding receivables
    - Invoices that need follow-up
    - Late payments from customers

    Args:
        days_overdue: Minimum days past due (0 = all unpaid, 30 = 30+ days overdue)

    Returns:
        List of outstanding invoices with aging information
    """
    try:
        ops = _get_finance_ops()
        invoices = ops.get_outstanding_invoices(days_overdue=days_overdue)

        return [
            {
                "id": inv.get('id'),
                "number": inv.get('name'),
                "customer": inv.get('partner_id', [None, 'Unknown'])[1] if inv.get('partner_id') else 'Unknown',
                "invoice_date": inv.get('invoice_date'),
                "due_date": inv.get('invoice_date_due'),
                "total": inv.get('amount_total', 0),
                "balance_due": inv.get('amount_residual', 0),
                "days_overdue": inv.get('days_overdue', 0),
                "priority": "high" if inv.get('days_overdue', 0) > 30 else "medium" if inv.get('days_overdue', 0) > 0 else "normal"
            }
            for inv in invoices
        ]

    except Exception as e:
        logger.error(f"Error getting outstanding invoices: {e}")
        return [{"error": str(e)}]


# ==================== Payment Tools ====================

@tool
def search_payments(
    partner_name: Optional[str] = None,
    payment_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search payment records.

    Use this tool when the user wants to:
    - List or search payments
    - See payments from/to a specific partner
    - Track recent payments
    - View payment history

    Args:
        partner_name: Filter by partner name (partial match)
        payment_type: Filter by type - "inbound" (received) or "outbound" (sent)
        date_from: Filter from date (YYYY-MM-DD)
        date_to: Filter to date (YYYY-MM-DD)
        limit: Maximum results (default 20)

    Returns:
        List of payment records
    """
    try:
        ops = _get_finance_ops()
        payments = ops.search_payments(
            partner_name=partner_name,
            payment_type=payment_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit
        )

        return [
            {
                "id": pay.get('id'),
                "reference": pay.get('name'),
                "partner": pay.get('partner_id', [None, 'N/A'])[1] if pay.get('partner_id') else 'N/A',
                "amount": pay.get('amount', 0),
                "date": pay.get('date'),
                "type": "Received" if pay.get('payment_type') == 'inbound' else "Sent",
                "journal": pay.get('journal_id', [None, 'N/A'])[1] if pay.get('journal_id') else 'N/A',
                "status": pay.get('state')
            }
            for pay in payments
        ]

    except Exception as e:
        logger.error(f"Error searching payments: {e}")
        return [{"error": str(e)}]


@tool
def get_payment_details(payment_id: int) -> Dict[str, Any]:
    """
    Get detailed payment information.

    Use this tool when the user wants:
    - Full details of a specific payment
    - Invoices linked to a payment

    Args:
        payment_id: The payment record ID

    Returns:
        Complete payment details with linked invoices
    """
    try:
        ops = _get_finance_ops()
        payment = ops.get_payment_details(payment_id)

        if not payment:
            return {"error": f"Payment with ID {payment_id} not found"}

        result = {
            "id": payment.get('id'),
            "reference": payment.get('name'),
            "partner": payment.get('partner_id', [None, 'N/A'])[1] if payment.get('partner_id') else 'N/A',
            "amount": payment.get('amount', 0),
            "date": payment.get('date'),
            "type": "Received" if payment.get('payment_type') == 'inbound' else "Sent",
            "journal": payment.get('journal_id', [None, 'N/A'])[1] if payment.get('journal_id') else 'N/A',
            "status": payment.get('state'),
            "related_invoices": payment.get('related_invoices', [])
        }

        return result

    except Exception as e:
        logger.error(f"Error getting payment details: {e}")
        return {"error": str(e)}


# ==================== Report Tools ====================

@tool
def get_profit_loss_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get Profit & Loss report.

    Use this tool when the user asks about:
    - Profit and loss / P&L
    - Net profit or net income
    - Revenue vs expenses
    - How profitable the company is
    - Monthly/quarterly earnings

    Args:
        date_from: Start date (YYYY-MM-DD). Defaults to start of current month.
        date_to: End date (YYYY-MM-DD). Defaults to today.

    Returns:
        P&L summary with revenue and expense breakdown
    """
    try:
        ops = _get_finance_ops()
        pl = ops.get_profit_loss(date_from=date_from, date_to=date_to)

        return {
            "period": {
                "from": pl.get('date_from'),
                "to": pl.get('date_to')
            },
            "total_revenue": pl.get('total_revenue', 0),
            "total_expenses": pl.get('total_expenses', 0),
            "net_profit": pl.get('net_profit', 0),
            "profit_margin": round(pl.get('net_profit', 0) / pl.get('total_revenue', 1) * 100, 1) if pl.get('total_revenue', 0) > 0 else 0,
            "revenue_breakdown": pl.get('revenue_breakdown', [])[:10],  # Top 10
            "expense_breakdown": pl.get('expense_breakdown', [])[:10]   # Top 10
        }

    except Exception as e:
        logger.error(f"Error getting P&L report: {e}")
        return {"error": str(e)}


@tool
def get_cash_flow_summary(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get cash flow summary.

    Use this tool when the user asks about:
    - Cash flow
    - Cash position
    - Money coming in/going out
    - Bank balance
    - Liquidity

    Args:
        date_from: Start date (YYYY-MM-DD). Defaults to start of current month.
        date_to: End date (YYYY-MM-DD). Defaults to today.

    Returns:
        Cash flow with inflows, outflows, and balance by account
    """
    try:
        ops = _get_finance_ops()
        cf = ops.get_cash_flow(date_from=date_from, date_to=date_to)

        return {
            "period": {
                "from": cf.get('date_from'),
                "to": cf.get('date_to')
            },
            "total_inflows": cf.get('total_inflows', 0),
            "total_outflows": cf.get('total_outflows', 0),
            "net_cash_flow": cf.get('net_cash_flow', 0),
            "current_balance": cf.get('current_balance', 0),
            "by_account": cf.get('by_journal', [])
        }

    except Exception as e:
        logger.error(f"Error getting cash flow: {e}")
        return {"error": str(e)}


@tool
def get_expense_analysis(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get expense breakdown by category.

    Use this tool when the user asks about:
    - Expense breakdown
    - Where money is being spent
    - Cost analysis
    - Expense categories

    Args:
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)

    Returns:
        Expense breakdown with categories and percentages
    """
    try:
        ops = _get_finance_ops()
        expenses = ops.get_expense_breakdown(date_from=date_from, date_to=date_to)

        return {
            "period": {
                "from": expenses.get('date_from'),
                "to": expenses.get('date_to')
            },
            "total_expenses": expenses.get('total_expenses', 0),
            "categories": expenses.get('categories', [])[:15]  # Top 15 categories
        }

    except Exception as e:
        logger.error(f"Error getting expense analysis: {e}")
        return {"error": str(e)}


@tool
def get_revenue_analysis(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get revenue breakdown by source.

    Use this tool when the user asks about:
    - Revenue breakdown
    - Income sources
    - Sales by customer
    - Where money is coming from

    Args:
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)

    Returns:
        Revenue breakdown by account and customer
    """
    try:
        ops = _get_finance_ops()
        revenue = ops.get_revenue_breakdown(date_from=date_from, date_to=date_to)

        return {
            "period": {
                "from": revenue.get('date_from'),
                "to": revenue.get('date_to')
            },
            "total_revenue": revenue.get('total_revenue', 0),
            "by_account": revenue.get('by_account', [])[:10],
            "top_customers": revenue.get('by_customer', [])[:10]
        }

    except Exception as e:
        logger.error(f"Error getting revenue analysis: {e}")
        return {"error": str(e)}


# ==================== Journal Tools ====================

@tool
def get_journal_entries(
    journal_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get journal entries.

    Use this tool when the user asks about:
    - Journal entries
    - Accounting entries
    - General ledger entries

    Args:
        journal_id: Filter by specific journal ID
        date_from: Filter from date (YYYY-MM-DD)
        date_to: Filter to date (YYYY-MM-DD)
        limit: Maximum results (default 20)

    Returns:
        List of journal entries
    """
    try:
        ops = _get_finance_ops()
        entries = ops.search_journal_entries(
            journal_id=journal_id,
            date_from=date_from,
            date_to=date_to,
            limit=limit
        )

        return [
            {
                "id": entry.get('id'),
                "number": entry.get('name'),
                "date": entry.get('date'),
                "journal": entry.get('journal_id', [None, 'N/A'])[1] if entry.get('journal_id') else 'N/A',
                "reference": entry.get('ref'),
                "amount": entry.get('amount_total', 0),
                "status": entry.get('state')
            }
            for entry in entries
        ]

    except Exception as e:
        logger.error(f"Error getting journal entries: {e}")
        return [{"error": str(e)}]


@tool
def create_journal_entry(
    journal_id: int,
    date: str,
    reference: str,
    lines: List[Dict[str, Any]],
    auto_post: bool = False
) -> Dict[str, Any]:
    """
    Create a new journal entry.

    Use this tool when the user wants to:
    - Record a journal entry
    - Create an accounting entry
    - Make a manual adjustment

    IMPORTANT: Entry must be balanced (total debits = total credits)

    Args:
        journal_id: The journal ID to post to
        date: Entry date (YYYY-MM-DD)
        reference: Description/reference for the entry
        lines: List of line items, each with:
            - account_id: Account ID (required)
            - debit: Debit amount (default 0)
            - credit: Credit amount (default 0)
            - name: Line description (optional)
            - partner_id: Partner ID (optional)
        auto_post: Whether to post immediately (default False = draft)

    Returns:
        Created entry details or error if unbalanced
    """
    try:
        ops = _get_finance_ops()
        result = ops.create_journal_entry(
            journal_id=journal_id,
            date=date,
            ref=reference,
            lines=lines,
            auto_post=auto_post
        )

        return result

    except Exception as e:
        logger.error(f"Error creating journal entry: {e}")
        return {"error": str(e)}


@tool
def get_journals() -> List[Dict[str, Any]]:
    """
    Get list of accounting journals.

    Use this tool when the user needs:
    - List of journals to choose from
    - Journal IDs for creating entries
    - Available accounting journals

    Returns:
        List of journals with IDs and types
    """
    try:
        ops = _get_finance_ops()
        journals = ops.get_journals()

        return [
            {
                "id": j.get('id'),
                "name": j.get('name'),
                "code": j.get('code'),
                "type": j.get('type')
            }
            for j in journals
        ]

    except Exception as e:
        logger.error(f"Error getting journals: {e}")
        return [{"error": str(e)}]


# ==================== Sales Tools ====================

@tool
def get_sales_summary(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get sales summary with totals, order count, and top performers.

    Use this tool when the user asks about:
    - Sales summary / overview
    - Total sales / sales numbers
    - How much we sold
    - Sales performance
    - كام المبيعات / اجمالي المبيعات

    Args:
        date_from: Start date (YYYY-MM-DD). Defaults to start of current month.
        date_to: End date (YYYY-MM-DD). Defaults to today.

    Returns:
        Sales summary with totals, order count, top products, and top customers
    """
    try:
        ops = _get_finance_ops()
        summary = ops.get_sales_summary(date_from=date_from, date_to=date_to)

        return {
            "period": {
                "from": summary.get('date_from'),
                "to": summary.get('date_to')
            },
            "total_sales": summary.get('total_sales', 0),
            "order_count": summary.get('order_count', 0),
            "average_order_value": summary.get('average_order_value', 0),
            "top_products": summary.get('top_products', [])[:5],
            "top_customers": summary.get('top_customers', [])[:5]
        }

    except Exception as e:
        logger.error(f"Error getting sales summary: {e}")
        return {"error": str(e)}


@tool
def search_sales_orders(
    partner_name: Optional[str] = None,
    state: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    salesperson: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search sales orders in Odoo.

    Use this tool when the user wants to:
    - List or search sales orders
    - Find orders for a specific customer
    - See recent sales
    - Filter orders by status or salesperson
    - عايز اشوف الأوردرات / طلبات البيع

    Args:
        partner_name: Filter by customer name (partial match)
        state: Filter by state - "draft", "sent", "sale", "done", "cancel"
        date_from: Filter from date (YYYY-MM-DD)
        date_to: Filter to date (YYYY-MM-DD)
        salesperson: Filter by salesperson name
        limit: Maximum results to return (default 20)

    Returns:
        List of matching sales orders
    """
    try:
        ops = _get_finance_ops()
        orders = ops.search_sales_orders(
            partner_name=partner_name,
            state=state,
            date_from=date_from,
            date_to=date_to,
            salesperson=salesperson,
            limit=limit
        )

        return [
            {
                "id": order.get('id'),
                "number": order.get('name'),
                "customer": order.get('partner_id', [None, 'N/A'])[1] if order.get('partner_id') else 'N/A',
                "date": order.get('date_order'),
                "salesperson": order.get('user_id', [None, 'N/A'])[1] if order.get('user_id') else 'N/A',
                "total": order.get('amount_total', 0),
                "status": order.get('state'),
                "invoice_status": order.get('invoice_status')
            }
            for order in orders
        ]

    except Exception as e:
        logger.error(f"Error searching sales orders: {e}")
        return [{"error": str(e)}]


@tool
def get_sales_order_details(order_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific sales order.

    Use this tool when the user wants:
    - Full details of a specific sales order
    - Order line items
    - Order history / status

    Args:
        order_id: The Odoo sales order record ID

    Returns:
        Complete sales order details including line items
    """
    try:
        ops = _get_finance_ops()
        order = ops.get_sales_order_details(order_id)

        if not order:
            return {"error": f"Sales order with ID {order_id} not found"}

        return {
            "id": order.get('id'),
            "number": order.get('name'),
            "customer": order.get('partner_id', [None, 'N/A'])[1] if order.get('partner_id') else 'N/A',
            "date": order.get('date_order'),
            "salesperson": order.get('user_id', [None, 'N/A'])[1] if order.get('user_id') else 'N/A',
            "total": order.get('amount_total', 0),
            "subtotal": order.get('amount_untaxed', 0),
            "tax": order.get('amount_tax', 0),
            "status": order.get('state'),
            "invoice_status": order.get('invoice_status'),
            "reference": order.get('client_order_ref'),
            "lines": [
                {
                    "product": line.get('product_id', [None, line.get('name', 'N/A')])[1] if line.get('product_id') else line.get('name', 'N/A'),
                    "quantity": line.get('product_uom_qty', 0),
                    "unit_price": line.get('price_unit', 0),
                    "subtotal": line.get('price_subtotal', 0)
                }
                for line in order.get('order_lines', [])
            ]
        }

    except Exception as e:
        logger.error(f"Error getting sales order details: {e}")
        return {"error": str(e)}


@tool
def get_top_selling_products(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get top selling products by revenue.

    Use this tool when the user asks about:
    - Best selling products
    - Top products
    - Product sales ranking
    - ايه اكتر المنتجات مبيعاً

    Args:
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        limit: Number of products to return (default 10)

    Returns:
        List of top selling products with quantities and revenue
    """
    try:
        ops = _get_finance_ops()
        products = ops.get_top_selling_products(
            date_from=date_from,
            date_to=date_to,
            limit=limit
        )

        return products

    except Exception as e:
        logger.error(f"Error getting top selling products: {e}")
        return [{"error": str(e)}]


@tool
def get_sales_by_customer(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get sales breakdown by customer.

    Use this tool when the user asks about:
    - Sales by customer
    - Top customers
    - Customer ranking / performance
    - Best customers
    - مين اكتر عملاء بيشتروا

    Args:
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        limit: Number of customers to return (default 10)

    Returns:
        List of top customers with order count and total revenue
    """
    try:
        ops = _get_finance_ops()
        customers = ops.get_sales_by_customer(
            date_from=date_from,
            date_to=date_to,
            limit=limit
        )

        return customers

    except Exception as e:
        logger.error(f"Error getting sales by customer: {e}")
        return [{"error": str(e)}]


# Export all tools as a list
finance_tools = [
    # Summary
    get_financial_summary,
    # Invoices
    search_invoices,
    get_invoice_details,
    get_outstanding_invoices,
    # Payments
    search_payments,
    get_payment_details,
    # Reports
    get_profit_loss_report,
    get_cash_flow_summary,
    get_expense_analysis,
    get_revenue_analysis,
    # Journals
    get_journal_entries,
    create_journal_entry,
    get_journals,
    # Sales
    get_sales_summary,
    search_sales_orders,
    get_sales_order_details,
    get_top_selling_products,
    get_sales_by_customer,
]
