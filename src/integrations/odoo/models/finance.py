"""
Finance Model Operations

Operations for accounting and financial management in Odoo.
"""

from typing import Dict, List, Any, Optional
from datetime import date, datetime, timedelta
import logging

from src.integrations.odoo.client import OdooClient, get_odoo_client

logger = logging.getLogger(__name__)


class FinanceOperations:
    """Finance and accounting operations for Odoo."""

    def __init__(self, client: Optional[OdooClient] = None):
        """
        Initialize finance operations.

        Args:
            client: Optional Odoo client. Uses singleton if not provided.
        """
        self.client = client or get_odoo_client()

    # ==================== Financial Summary ====================

    def get_financial_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive financial summary.

        Returns:
            Dictionary with receivables, payables, cash balance, and alerts
        """
        summary = {
            'total_receivables': 0,
            'total_payables': 0,
            'cash_balance': 0,
            'overdue_count': 0,
            'overdue_amount': 0,
        }

        try:
            # Get total receivables (customer invoices - out_invoice)
            receivables = self.client.search_read(
                'account.move',
                [
                    ['move_type', '=', 'out_invoice'],
                    ['state', '=', 'posted'],
                    ['payment_state', 'in', ['not_paid', 'partial']]
                ],
                fields=['amount_residual'],
                limit=1000
            )
            summary['total_receivables'] = sum(r.get('amount_residual', 0) for r in receivables)

            # Get total payables (vendor bills - in_invoice)
            payables = self.client.search_read(
                'account.move',
                [
                    ['move_type', '=', 'in_invoice'],
                    ['state', '=', 'posted'],
                    ['payment_state', 'in', ['not_paid', 'partial']]
                ],
                fields=['amount_residual'],
                limit=1000
            )
            summary['total_payables'] = sum(p.get('amount_residual', 0) for p in payables)

            # Get cash balance from bank journals
            bank_journals = self.client.search_read(
                'account.journal',
                [['type', 'in', ['bank', 'cash']]],
                fields=['id', 'name']
            )

            if bank_journals:
                journal_ids = [j['id'] for j in bank_journals]
                # Get account balances
                for journal in bank_journals:
                    accounts = self.client.search_read(
                        'account.move.line',
                        [
                            ['journal_id', '=', journal['id']],
                            ['parent_state', '=', 'posted']
                        ],
                        fields=['balance'],
                        limit=5000
                    )
                    summary['cash_balance'] += sum(a.get('balance', 0) for a in accounts)

            # Get overdue invoices
            today = date.today().isoformat()
            overdue = self.client.search_read(
                'account.move',
                [
                    ['move_type', '=', 'out_invoice'],
                    ['state', '=', 'posted'],
                    ['payment_state', 'in', ['not_paid', 'partial']],
                    ['invoice_date_due', '<', today]
                ],
                fields=['amount_residual'],
                limit=1000
            )
            summary['overdue_count'] = len(overdue)
            summary['overdue_amount'] = sum(o.get('amount_residual', 0) for o in overdue)

        except Exception as e:
            logger.error(f"Error getting financial summary: {e}")
            summary['error'] = str(e)

        return summary

    # ==================== Invoice Operations ====================

    def search_invoices(
        self,
        partner_name: Optional[str] = None,
        state: Optional[str] = None,
        move_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        payment_state: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search invoices based on criteria.

        Args:
            partner_name: Filter by customer/vendor name (partial match)
            state: Filter by state (draft, posted, cancel)
            move_type: Filter by type (out_invoice, in_invoice, out_refund, in_refund)
            date_from: Filter from date (YYYY-MM-DD)
            date_to: Filter to date (YYYY-MM-DD)
            payment_state: Filter by payment state (not_paid, partial, paid)
            limit: Maximum records to return

        Returns:
            List of matching invoices
        """
        domain = [['move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']]]

        if partner_name:
            domain.append(['partner_id.name', 'ilike', partner_name])

        if state:
            domain.append(['state', '=', state])

        if move_type:
            domain.append(['move_type', '=', move_type])

        if date_from:
            domain.append(['invoice_date', '>=', date_from])

        if date_to:
            domain.append(['invoice_date', '<=', date_to])

        if payment_state:
            domain.append(['payment_state', '=', payment_state])

        return self.client.search_read(
            'account.move',
            domain,
            fields=[
                'name', 'partner_id', 'invoice_date', 'invoice_date_due',
                'amount_total', 'amount_residual', 'amount_untaxed', 'amount_tax',
                'state', 'payment_state', 'move_type', 'currency_id', 'ref'
            ],
            limit=limit,
            order='invoice_date desc'
        )

    def get_invoice_details(self, invoice_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific invoice.

        Args:
            invoice_id: Odoo invoice record ID

        Returns:
            Complete invoice details including line items
        """
        invoices = self.client.read('account.move', [invoice_id])
        if not invoices:
            return {}

        invoice = invoices[0]

        # Get invoice line items
        lines = self.client.search_read(
            'account.move.line',
            [
                ['move_id', '=', invoice_id],
                ['display_type', 'in', ['product', False]]
            ],
            fields=[
                'name', 'product_id', 'quantity', 'price_unit',
                'price_subtotal', 'price_total', 'tax_ids', 'account_id'
            ]
        )
        invoice['invoice_lines'] = lines

        # Get payment info if any
        if invoice.get('payment_state') in ['partial', 'paid']:
            payments = self.client.search_read(
                'account.payment',
                [['ref', 'ilike', invoice.get('name', '')]],
                fields=['name', 'amount', 'date', 'state', 'payment_type'],
                limit=20
            )
            invoice['payments'] = payments

        return invoice

    def get_outstanding_invoices(self, days_overdue: int = 0) -> List[Dict[str, Any]]:
        """
        Get invoices that are unpaid or overdue.

        Args:
            days_overdue: Minimum days past due (0 = all unpaid)

        Returns:
            List of outstanding invoices with aging info
        """
        today = date.today()
        domain = [
            ['move_type', '=', 'out_invoice'],
            ['state', '=', 'posted'],
            ['payment_state', 'in', ['not_paid', 'partial']]
        ]

        if days_overdue > 0:
            due_date = (today - timedelta(days=days_overdue)).isoformat()
            domain.append(['invoice_date_due', '<=', due_date])

        invoices = self.client.search_read(
            'account.move',
            domain,
            fields=[
                'name', 'partner_id', 'invoice_date', 'invoice_date_due',
                'amount_total', 'amount_residual', 'currency_id'
            ],
            order='invoice_date_due asc',
            limit=100
        )

        # Add days overdue calculation
        for inv in invoices:
            if inv.get('invoice_date_due'):
                due = datetime.strptime(inv['invoice_date_due'], '%Y-%m-%d').date()
                inv['days_overdue'] = max(0, (today - due).days)
            else:
                inv['days_overdue'] = 0

        return invoices

    # ==================== Payment Operations ====================

    def search_payments(
        self,
        partner_name: Optional[str] = None,
        payment_type: Optional[str] = None,
        state: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search payment records.

        Args:
            partner_name: Filter by partner name
            payment_type: Filter by type (inbound, outbound)
            state: Filter by state (draft, posted, cancelled)
            date_from: Filter from date
            date_to: Filter to date
            limit: Maximum records

        Returns:
            List of payment records
        """
        domain = []

        if partner_name:
            domain.append(['partner_id.name', 'ilike', partner_name])

        if payment_type:
            domain.append(['payment_type', '=', payment_type])

        if state:
            domain.append(['state', '=', state])

        if date_from:
            domain.append(['date', '>=', date_from])

        if date_to:
            domain.append(['date', '<=', date_to])

        return self.client.search_read(
            'account.payment',
            domain,
            fields=[
                'name', 'partner_id', 'amount', 'date', 'state',
                'payment_type', 'journal_id', 'currency_id', 'ref'
            ],
            limit=limit,
            order='date desc'
        )

    def get_payment_details(self, payment_id: int) -> Dict[str, Any]:
        """
        Get detailed payment information.

        Args:
            payment_id: Payment record ID

        Returns:
            Complete payment details
        """
        payments = self.client.read('account.payment', [payment_id])
        if not payments:
            return {}

        payment = payments[0]

        # Get related invoices if available
        if payment.get('reconciled_invoice_ids'):
            invoices = self.client.search_read(
                'account.move',
                [['id', 'in', payment['reconciled_invoice_ids']]],
                fields=['name', 'amount_total', 'invoice_date']
            )
            payment['related_invoices'] = invoices

        return payment

    # ==================== Journal Operations ====================

    def get_journals(self, journal_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get accounting journals.

        Args:
            journal_type: Filter by type (sale, purchase, cash, bank, general)

        Returns:
            List of journals
        """
        domain = []
        if journal_type:
            domain.append(['type', '=', journal_type])

        return self.client.search_read(
            'account.journal',
            domain,
            fields=['name', 'code', 'type', 'currency_id', 'company_id'],
            order='name asc'
        )

    def search_journal_entries(
        self,
        journal_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search journal entries.

        Args:
            journal_id: Filter by journal
            date_from: Filter from date
            date_to: Filter to date
            limit: Maximum records

        Returns:
            List of journal entries
        """
        domain = [['move_type', '=', 'entry']]

        if journal_id:
            domain.append(['journal_id', '=', journal_id])

        if date_from:
            domain.append(['date', '>=', date_from])

        if date_to:
            domain.append(['date', '<=', date_to])

        return self.client.search_read(
            'account.move',
            domain,
            fields=[
                'name', 'date', 'journal_id', 'ref',
                'amount_total', 'state', 'partner_id'
            ],
            limit=limit,
            order='date desc'
        )

    def create_journal_entry(
        self,
        journal_id: int,
        date: str,
        ref: str,
        lines: List[Dict[str, Any]],
        auto_post: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new journal entry.

        Args:
            journal_id: Journal ID
            date: Entry date (YYYY-MM-DD)
            ref: Reference/description
            lines: List of line items [{'account_id': x, 'debit': x, 'credit': x, 'name': x}]
            auto_post: Whether to post immediately

        Returns:
            Created entry details
        """
        # Validate balanced entry
        total_debit = sum(l.get('debit', 0) for l in lines)
        total_credit = sum(l.get('credit', 0) for l in lines)

        if abs(total_debit - total_credit) > 0.01:
            return {'error': f'Unbalanced entry: Debit={total_debit}, Credit={total_credit}'}

        # Format lines for Odoo
        line_ids = []
        for line in lines:
            line_ids.append((0, 0, {
                'account_id': line['account_id'],
                'name': line.get('name', ref),
                'debit': line.get('debit', 0),
                'credit': line.get('credit', 0),
                'partner_id': line.get('partner_id', False),
            }))

        values = {
            'journal_id': journal_id,
            'date': date,
            'ref': ref,
            'move_type': 'entry',
            'line_ids': line_ids,
        }

        try:
            entry_id = self.client.create('account.move', values)

            if auto_post:
                self.client.call_method('account.move', 'action_post', [entry_id])

            return {
                'id': entry_id,
                'journal_id': journal_id,
                'date': date,
                'ref': ref,
                'total_amount': total_debit,
                'state': 'posted' if auto_post else 'draft'
            }

        except Exception as e:
            logger.error(f"Error creating journal entry: {e}")
            return {'error': str(e)}

    # ==================== Reports ====================

    def get_profit_loss(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get profit and loss data.

        Args:
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)

        Returns:
            P&L summary with revenue and expense breakdown
        """
        if not date_from:
            date_from = date.today().replace(day=1).isoformat()
        if not date_to:
            date_to = date.today().isoformat()

        result = {
            'date_from': date_from,
            'date_to': date_to,
            'total_revenue': 0,
            'total_expenses': 0,
            'net_profit': 0,
            'revenue_breakdown': [],
            'expense_breakdown': []
        }

        try:
            # Get revenue accounts (income type)
            revenue_accounts = self.client.search_read(
                'account.account',
                [['account_type', 'in', ['income', 'income_other']]],
                fields=['id', 'name', 'code']
            )

            for acc in revenue_accounts:
                lines = self.client.search_read(
                    'account.move.line',
                    [
                        ['account_id', '=', acc['id']],
                        ['date', '>=', date_from],
                        ['date', '<=', date_to],
                        ['parent_state', '=', 'posted']
                    ],
                    fields=['credit', 'debit']
                )
                amount = sum(l.get('credit', 0) - l.get('debit', 0) for l in lines)
                if abs(amount) > 0:
                    result['revenue_breakdown'].append({
                        'account': acc['name'],
                        'code': acc['code'],
                        'amount': amount
                    })
                    result['total_revenue'] += amount

            # Get expense accounts
            expense_accounts = self.client.search_read(
                'account.account',
                [['account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost']]],
                fields=['id', 'name', 'code']
            )

            for acc in expense_accounts:
                lines = self.client.search_read(
                    'account.move.line',
                    [
                        ['account_id', '=', acc['id']],
                        ['date', '>=', date_from],
                        ['date', '<=', date_to],
                        ['parent_state', '=', 'posted']
                    ],
                    fields=['credit', 'debit']
                )
                amount = sum(l.get('debit', 0) - l.get('credit', 0) for l in lines)
                if abs(amount) > 0:
                    result['expense_breakdown'].append({
                        'account': acc['name'],
                        'code': acc['code'],
                        'amount': amount
                    })
                    result['total_expenses'] += amount

            result['net_profit'] = result['total_revenue'] - result['total_expenses']

        except Exception as e:
            logger.error(f"Error getting P&L: {e}")
            result['error'] = str(e)

        return result

    def get_cash_flow(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get cash flow summary.

        Args:
            date_from: Start date
            date_to: End date

        Returns:
            Cash flow with inflows, outflows, and balance
        """
        if not date_from:
            date_from = date.today().replace(day=1).isoformat()
        if not date_to:
            date_to = date.today().isoformat()

        result = {
            'date_from': date_from,
            'date_to': date_to,
            'total_inflows': 0,
            'total_outflows': 0,
            'net_cash_flow': 0,
            'current_balance': 0,
            'by_journal': []
        }

        try:
            # Get bank/cash journals
            journals = self.client.search_read(
                'account.journal',
                [['type', 'in', ['bank', 'cash']]],
                fields=['id', 'name', 'type']
            )

            for journal in journals:
                # Get transactions for this journal
                lines = self.client.search_read(
                    'account.move.line',
                    [
                        ['journal_id', '=', journal['id']],
                        ['date', '>=', date_from],
                        ['date', '<=', date_to],
                        ['parent_state', '=', 'posted']
                    ],
                    fields=['debit', 'credit', 'balance']
                )

                inflows = sum(l.get('debit', 0) for l in lines)
                outflows = sum(l.get('credit', 0) for l in lines)

                result['by_journal'].append({
                    'journal': journal['name'],
                    'type': journal['type'],
                    'inflows': inflows,
                    'outflows': outflows,
                    'net': inflows - outflows
                })

                result['total_inflows'] += inflows
                result['total_outflows'] += outflows

            result['net_cash_flow'] = result['total_inflows'] - result['total_outflows']

            # Get current balance
            all_lines = self.client.search_read(
                'account.move.line',
                [
                    ['journal_id', 'in', [j['id'] for j in journals]],
                    ['parent_state', '=', 'posted']
                ],
                fields=['balance'],
                limit=10000
            )
            result['current_balance'] = sum(l.get('balance', 0) for l in all_lines)

        except Exception as e:
            logger.error(f"Error getting cash flow: {e}")
            result['error'] = str(e)

        return result

    def get_expense_breakdown(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get expense breakdown by account/category.

        Args:
            date_from: Start date
            date_to: End date

        Returns:
            Expense breakdown with totals and percentages
        """
        if not date_from:
            date_from = date.today().replace(day=1).isoformat()
        if not date_to:
            date_to = date.today().isoformat()

        result = {
            'date_from': date_from,
            'date_to': date_to,
            'total_expenses': 0,
            'categories': []
        }

        try:
            # Get expense accounts
            accounts = self.client.search_read(
                'account.account',
                [['account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost']]],
                fields=['id', 'name', 'code']
            )

            for acc in accounts:
                lines = self.client.search_read(
                    'account.move.line',
                    [
                        ['account_id', '=', acc['id']],
                        ['date', '>=', date_from],
                        ['date', '<=', date_to],
                        ['parent_state', '=', 'posted']
                    ],
                    fields=['debit', 'credit']
                )
                amount = sum(l.get('debit', 0) - l.get('credit', 0) for l in lines)
                if amount > 0:
                    result['categories'].append({
                        'account': acc['name'],
                        'code': acc['code'],
                        'amount': amount
                    })
                    result['total_expenses'] += amount

            # Calculate percentages
            if result['total_expenses'] > 0:
                for cat in result['categories']:
                    cat['percentage'] = round(cat['amount'] / result['total_expenses'] * 100, 1)

            # Sort by amount descending
            result['categories'].sort(key=lambda x: x['amount'], reverse=True)

        except Exception as e:
            logger.error(f"Error getting expense breakdown: {e}")
            result['error'] = str(e)

        return result

    def get_revenue_breakdown(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get revenue breakdown by source.

        Args:
            date_from: Start date
            date_to: End date

        Returns:
            Revenue breakdown with totals
        """
        if not date_from:
            date_from = date.today().replace(day=1).isoformat()
        if not date_to:
            date_to = date.today().isoformat()

        result = {
            'date_from': date_from,
            'date_to': date_to,
            'total_revenue': 0,
            'by_account': [],
            'by_customer': []
        }

        try:
            # Revenue by account
            accounts = self.client.search_read(
                'account.account',
                [['account_type', 'in', ['income', 'income_other']]],
                fields=['id', 'name', 'code']
            )

            for acc in accounts:
                lines = self.client.search_read(
                    'account.move.line',
                    [
                        ['account_id', '=', acc['id']],
                        ['date', '>=', date_from],
                        ['date', '<=', date_to],
                        ['parent_state', '=', 'posted']
                    ],
                    fields=['credit', 'debit']
                )
                amount = sum(l.get('credit', 0) - l.get('debit', 0) for l in lines)
                if amount > 0:
                    result['by_account'].append({
                        'account': acc['name'],
                        'code': acc['code'],
                        'amount': amount
                    })
                    result['total_revenue'] += amount

            # Revenue by customer (from invoices)
            invoices = self.client.search_read(
                'account.move',
                [
                    ['move_type', '=', 'out_invoice'],
                    ['state', '=', 'posted'],
                    ['invoice_date', '>=', date_from],
                    ['invoice_date', '<=', date_to]
                ],
                fields=['partner_id', 'amount_untaxed']
            )

            customer_totals = {}
            for inv in invoices:
                if inv.get('partner_id'):
                    customer = inv['partner_id'][1]
                    customer_totals[customer] = customer_totals.get(customer, 0) + inv.get('amount_untaxed', 0)

            result['by_customer'] = [
                {'customer': k, 'amount': v}
                for k, v in sorted(customer_totals.items(), key=lambda x: x[1], reverse=True)
            ][:20]  # Top 20 customers

        except Exception as e:
            logger.error(f"Error getting revenue breakdown: {e}")
            result['error'] = str(e)

        return result

    # ==================== Alerts ====================

    def get_overdue_alerts(self, days_threshold: int = 30) -> List[Dict[str, Any]]:
        """
        Get alerts for overdue invoices.

        Args:
            days_threshold: Days overdue to trigger high priority

        Returns:
            List of overdue invoice alerts
        """
        overdue = self.get_outstanding_invoices(days_overdue=1)

        alerts = []
        for inv in overdue:
            priority = 'high' if inv.get('days_overdue', 0) > days_threshold else 'medium'
            alerts.append({
                'type': 'overdue_invoice',
                'priority': priority,
                'invoice': inv.get('name'),
                'customer': inv.get('partner_id', [None, 'Unknown'])[1] if inv.get('partner_id') else 'Unknown',
                'amount': inv.get('amount_residual', 0),
                'days_overdue': inv.get('days_overdue', 0),
                'message': f"Invoice {inv.get('name')} is {inv.get('days_overdue', 0)} days overdue"
            })

        return alerts

    def get_cash_flow_alerts(self, low_balance_threshold: float = 10000) -> List[Dict[str, Any]]:
        """
        Get cash flow warning alerts.

        Args:
            low_balance_threshold: Balance below which to alert

        Returns:
            List of cash flow alerts
        """
        alerts = []

        try:
            # Check bank balances
            journals = self.client.search_read(
                'account.journal',
                [['type', 'in', ['bank', 'cash']]],
                fields=['id', 'name']
            )

            for journal in journals:
                lines = self.client.search_read(
                    'account.move.line',
                    [
                        ['journal_id', '=', journal['id']],
                        ['parent_state', '=', 'posted']
                    ],
                    fields=['balance'],
                    limit=10000
                )
                balance = sum(l.get('balance', 0) for l in lines)

                if balance < low_balance_threshold:
                    alerts.append({
                        'type': 'low_cash_balance',
                        'priority': 'critical' if balance < low_balance_threshold / 2 else 'high',
                        'journal': journal['name'],
                        'balance': balance,
                        'threshold': low_balance_threshold,
                        'message': f"Low balance in {journal['name']}: {balance:,.2f}"
                    })

        except Exception as e:
            logger.error(f"Error checking cash flow alerts: {e}")

        return alerts

    def get_large_transaction_alerts(
        self,
        amount_threshold: float = 50000,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get alerts for large recent transactions.

        Args:
            amount_threshold: Amount above which to alert
            days_back: How many days back to check

        Returns:
            List of large transaction alerts
        """
        date_from = (date.today() - timedelta(days=days_back)).isoformat()

        alerts = []

        try:
            # Check large invoices
            large_invoices = self.client.search_read(
                'account.move',
                [
                    ['move_type', 'in', ['out_invoice', 'in_invoice']],
                    ['state', '=', 'posted'],
                    ['invoice_date', '>=', date_from],
                    ['amount_total', '>=', amount_threshold]
                ],
                fields=['name', 'partner_id', 'amount_total', 'move_type', 'invoice_date']
            )

            for inv in large_invoices:
                alerts.append({
                    'type': 'large_transaction',
                    'priority': 'medium',
                    'document': inv.get('name'),
                    'partner': inv.get('partner_id', [None, 'Unknown'])[1] if inv.get('partner_id') else 'Unknown',
                    'amount': inv.get('amount_total', 0),
                    'transaction_type': 'Customer Invoice' if inv.get('move_type') == 'out_invoice' else 'Vendor Bill',
                    'date': inv.get('invoice_date'),
                    'message': f"Large transaction: {inv.get('name')} for {inv.get('amount_total', 0):,.2f}"
                })

            # Check large payments
            large_payments = self.client.search_read(
                'account.payment',
                [
                    ['state', '=', 'posted'],
                    ['date', '>=', date_from],
                    ['amount', '>=', amount_threshold]
                ],
                fields=['name', 'partner_id', 'amount', 'payment_type', 'date']
            )

            for pay in large_payments:
                alerts.append({
                    'type': 'large_transaction',
                    'priority': 'medium',
                    'document': pay.get('name'),
                    'partner': pay.get('partner_id', [None, 'Unknown'])[1] if pay.get('partner_id') else 'Unknown',
                    'amount': pay.get('amount', 0),
                    'transaction_type': 'Payment Received' if pay.get('payment_type') == 'inbound' else 'Payment Sent',
                    'date': pay.get('date'),
                    'message': f"Large payment: {pay.get('name')} for {pay.get('amount', 0):,.2f}"
                })

        except Exception as e:
            logger.error(f"Error checking large transactions: {e}")

        return alerts

    def get_all_alerts(
        self,
        overdue_threshold: int = 30,
        cash_threshold: float = 10000,
        transaction_threshold: float = 50000
    ) -> Dict[str, Any]:
        """
        Get all financial alerts combined.

        Returns:
            Combined alerts from all categories
        """
        return {
            'overdue_invoices': self.get_overdue_alerts(overdue_threshold),
            'cash_flow': self.get_cash_flow_alerts(cash_threshold),
            'large_transactions': self.get_large_transaction_alerts(transaction_threshold),
            'total_alerts': 0  # Will be calculated below
        }

    # ==================== Sales Operations ====================

    def get_sales_summary(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get sales summary for a period.

        Args:
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)

        Returns:
            Sales summary with totals, order count, and breakdowns
        """
        if not date_from:
            # Default to current month
            date_from = date.today().replace(day=1).isoformat()
        if not date_to:
            date_to = date.today().isoformat()

        result = {
            'date_from': date_from,
            'date_to': date_to,
            'total_sales': 0,
            'order_count': 0,
            'average_order_value': 0,
            'confirmed_orders': 0,
            'draft_orders': 0,
            'top_products': [],
            'top_customers': [],
            'sales_by_salesperson': []
        }

        try:
            # Get all sales orders in the period
            orders = self.client.search_read(
                'sale.order',
                [
                    ['date_order', '>=', f"{date_from} 00:00:00"],
                    ['date_order', '<=', f"{date_to} 23:59:59"],
                    ['state', 'in', ['sale', 'done']]  # Confirmed/Done orders only
                ],
                fields=[
                    'name', 'partner_id', 'amount_total', 'amount_untaxed',
                    'date_order', 'state', 'user_id', 'currency_id'
                ],
                order='date_order desc'
            )

            result['order_count'] = len(orders)
            result['total_sales'] = sum(o.get('amount_total', 0) for o in orders)

            if result['order_count'] > 0:
                result['average_order_value'] = round(result['total_sales'] / result['order_count'], 2)

            # Count by state
            result['confirmed_orders'] = len([o for o in orders if o.get('state') == 'sale'])

            # Get draft orders count
            draft_orders = self.client.search_count(
                'sale.order',
                [
                    ['date_order', '>=', f"{date_from} 00:00:00"],
                    ['date_order', '<=', f"{date_to} 23:59:59"],
                    ['state', '=', 'draft']
                ]
            )
            result['draft_orders'] = draft_orders

            # Top customers
            customer_totals = {}
            for order in orders:
                if order.get('partner_id'):
                    customer = order['partner_id'][1]
                    customer_totals[customer] = customer_totals.get(customer, 0) + order.get('amount_total', 0)

            result['top_customers'] = [
                {'customer': k, 'total': v, 'order_count': len([o for o in orders if o.get('partner_id') and o['partner_id'][1] == k])}
                for k, v in sorted(customer_totals.items(), key=lambda x: x[1], reverse=True)
            ][:10]

            # Sales by salesperson
            salesperson_totals = {}
            for order in orders:
                if order.get('user_id'):
                    salesperson = order['user_id'][1]
                    if salesperson not in salesperson_totals:
                        salesperson_totals[salesperson] = {'total': 0, 'count': 0}
                    salesperson_totals[salesperson]['total'] += order.get('amount_total', 0)
                    salesperson_totals[salesperson]['count'] += 1

            result['sales_by_salesperson'] = [
                {'salesperson': k, 'total': v['total'], 'order_count': v['count']}
                for k, v in sorted(salesperson_totals.items(), key=lambda x: x[1]['total'], reverse=True)
            ]

            # Get top products from order lines
            order_ids = [o['id'] for o in orders]
            if order_ids:
                lines = self.client.search_read(
                    'sale.order.line',
                    [['order_id', 'in', order_ids]],
                    fields=['product_id', 'product_uom_qty', 'price_subtotal'],
                    limit=1000
                )

                product_totals = {}
                for line in lines:
                    if line.get('product_id'):
                        product = line['product_id'][1]
                        if product not in product_totals:
                            product_totals[product] = {'quantity': 0, 'revenue': 0}
                        product_totals[product]['quantity'] += line.get('product_uom_qty', 0)
                        product_totals[product]['revenue'] += line.get('price_subtotal', 0)

                result['top_products'] = [
                    {'product': k, 'quantity_sold': v['quantity'], 'revenue': v['revenue']}
                    for k, v in sorted(product_totals.items(), key=lambda x: x[1]['revenue'], reverse=True)
                ][:10]

        except Exception as e:
            logger.error(f"Error getting sales summary: {e}")
            result['error'] = str(e)

        return result

    def search_sales_orders(
        self,
        partner_name: Optional[str] = None,
        state: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        salesperson: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search sales orders.

        Args:
            partner_name: Filter by customer name
            state: Filter by state (draft, sent, sale, done, cancel)
            date_from: Filter from date
            date_to: Filter to date
            salesperson: Filter by salesperson name
            limit: Maximum records

        Returns:
            List of sales orders
        """
        domain = []

        if partner_name:
            domain.append(['partner_id.name', 'ilike', partner_name])

        if state:
            domain.append(['state', '=', state])

        if date_from:
            domain.append(['date_order', '>=', f"{date_from} 00:00:00"])

        if date_to:
            domain.append(['date_order', '<=', f"{date_to} 23:59:59"])

        if salesperson:
            domain.append(['user_id.name', 'ilike', salesperson])

        return self.client.search_read(
            'sale.order',
            domain,
            fields=[
                'name', 'partner_id', 'date_order', 'amount_total',
                'amount_untaxed', 'state', 'user_id', 'currency_id',
                'invoice_status', 'delivery_status'
            ],
            limit=limit,
            order='date_order desc'
        )

    def get_sales_order_details(self, order_id: int) -> Dict[str, Any]:
        """
        Get detailed sales order information.

        Args:
            order_id: Sales order ID

        Returns:
            Complete order details with lines
        """
        orders = self.client.read('sale.order', [order_id])
        if not orders:
            return {}

        order = orders[0]

        # Get order lines
        lines = self.client.search_read(
            'sale.order.line',
            [['order_id', '=', order_id]],
            fields=[
                'product_id', 'name', 'product_uom_qty', 'price_unit',
                'price_subtotal', 'price_total', 'discount', 'tax_id'
            ]
        )
        order['order_lines'] = lines

        return order

    def get_top_selling_products(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get top selling products.

        Args:
            date_from: Start date
            date_to: End date
            limit: Maximum products to return

        Returns:
            List of top products with quantities and revenue
        """
        if not date_from:
            date_from = date.today().replace(day=1).isoformat()
        if not date_to:
            date_to = date.today().isoformat()

        result = []

        try:
            # Get confirmed orders in period
            orders = self.client.search(
                'sale.order',
                [
                    ['date_order', '>=', f"{date_from} 00:00:00"],
                    ['date_order', '<=', f"{date_to} 23:59:59"],
                    ['state', 'in', ['sale', 'done']]
                ]
            )

            if orders:
                # Get all lines for these orders
                lines = self.client.search_read(
                    'sale.order.line',
                    [['order_id', 'in', orders]],
                    fields=['product_id', 'product_uom_qty', 'price_subtotal']
                )

                product_totals = {}
                for line in lines:
                    if line.get('product_id'):
                        pid = line['product_id'][0]
                        pname = line['product_id'][1]
                        if pid not in product_totals:
                            product_totals[pid] = {
                                'id': pid,
                                'name': pname,
                                'quantity': 0,
                                'revenue': 0,
                                'order_count': 0
                            }
                        product_totals[pid]['quantity'] += line.get('product_uom_qty', 0)
                        product_totals[pid]['revenue'] += line.get('price_subtotal', 0)
                        product_totals[pid]['order_count'] += 1

                result = sorted(
                    product_totals.values(),
                    key=lambda x: x['revenue'],
                    reverse=True
                )[:limit]

        except Exception as e:
            logger.error(f"Error getting top products: {e}")

        return result

    def get_sales_by_customer(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get sales breakdown by customer.

        Args:
            date_from: Start date
            date_to: End date
            limit: Maximum customers to return

        Returns:
            List of customers with their sales totals
        """
        if not date_from:
            date_from = date.today().replace(day=1).isoformat()
        if not date_to:
            date_to = date.today().isoformat()

        result = []

        try:
            orders = self.client.search_read(
                'sale.order',
                [
                    ['date_order', '>=', f"{date_from} 00:00:00"],
                    ['date_order', '<=', f"{date_to} 23:59:59"],
                    ['state', 'in', ['sale', 'done']]
                ],
                fields=['partner_id', 'amount_total', 'amount_untaxed']
            )

            customer_totals = {}
            for order in orders:
                if order.get('partner_id'):
                    cid = order['partner_id'][0]
                    cname = order['partner_id'][1]
                    if cid not in customer_totals:
                        customer_totals[cid] = {
                            'id': cid,
                            'name': cname,
                            'total': 0,
                            'order_count': 0
                        }
                    customer_totals[cid]['total'] += order.get('amount_total', 0)
                    customer_totals[cid]['order_count'] += 1

            result = sorted(
                customer_totals.values(),
                key=lambda x: x['total'],
                reverse=True
            )[:limit]

        except Exception as e:
            logger.error(f"Error getting sales by customer: {e}")

        return result
