"""
Contract Model Operations

Operations for contract management in Odoo.
Supports both OCA Contract module and Odoo Subscription module.
"""

from typing import Dict, List, Any, Optional
from datetime import date, datetime, timedelta
import logging

from src.integrations.odoo.client import OdooClient, get_odoo_client

logger = logging.getLogger(__name__)


class ContractOperations:
    """
    Contract-related operations for Odoo.

    Automatically detects which contract module is installed and adapts accordingly.
    Supports: OCA Contract (contract.contract), Odoo Subscription (sale.subscription)
    """

    # Possible contract models in order of preference
    CONTRACT_MODELS = [
        'contract.contract',      # OCA Contract module
        'sale.subscription',      # Odoo Enterprise Subscription
        'account.analytic.account',  # Fallback for older versions
    ]

    def __init__(self, client: Optional[OdooClient] = None):
        """
        Initialize contract operations.

        Args:
            client: Optional Odoo client. Uses singleton if not provided.
        """
        self.client = client or get_odoo_client()
        self._contract_model: Optional[str] = None
        self._model_fields: Optional[Dict[str, Any]] = None

    @property
    def contract_model(self) -> str:
        """
        Get the contract model name used in this Odoo instance.

        Returns:
            Model name string

        Raises:
            RuntimeError: If no contract module is found
        """
        if self._contract_model is None:
            self._contract_model = self._detect_contract_model()
        return self._contract_model

    def _detect_contract_model(self) -> str:
        """Detect which contract model is available."""
        for model in self.CONTRACT_MODELS:
            if self.client.check_model_exists(model):
                logger.info(f"Detected contract model: {model}")
                return model

        # If no dedicated contract model, log warning
        logger.warning("No dedicated contract module found. Using sale.order as fallback.")
        return 'sale.order'

    def _get_date_field(self) -> tuple[str, str]:
        """
        Get the date field names based on the contract model.

        Returns:
            Tuple of (start_date_field, end_date_field)
        """
        if self.contract_model == 'contract.contract':
            return ('date_start', 'date_end')
        elif self.contract_model == 'sale.subscription':
            return ('date_start', 'date')
        elif self.contract_model == 'sale.order':
            return ('date_order', 'validity_date')
        elif self.contract_model == 'account.analytic.account':
            # This model may not have date fields - use create_date as fallback
            return ('create_date', 'create_date')
        else:
            return ('date_start', 'date_end')

    def _has_state_field(self) -> bool:
        """Check if the contract model has a state field."""
        # account.analytic.account typically doesn't have state field
        return self.contract_model not in ['account.analytic.account']

    def _has_date_fields(self) -> bool:
        """Check if the contract model has date fields."""
        return self.contract_model not in ['account.analytic.account']

    def search_contracts(
        self,
        partner_name: Optional[str] = None,
        state: Optional[str] = None,
        expiring_within_days: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search contracts based on criteria.

        Args:
            partner_name: Filter by customer/vendor name (partial match)
            state: Filter by contract state
            expiring_within_days: Find contracts expiring within N days
            limit: Maximum records to return

        Returns:
            List of matching contracts
        """
        domain = []

        if partner_name:
            domain.append(['partner_id.name', 'ilike', partner_name])

        # Only filter by state if the model supports it
        if state and self._has_state_field():
            domain.append(['state', '=', state])

        # Only filter by date if the model supports it
        start_field, end_field = self._get_date_field()
        has_date_fields = self._has_date_fields()

        if expiring_within_days is not None and has_date_fields:
            end_date = date.today() + timedelta(days=expiring_within_days)
            domain.append([end_field, '<=', end_date.isoformat()])
            domain.append([end_field, '>=', date.today().isoformat()])

        # Basic fields that should exist on most models
        fields = ['name', 'partner_id', 'company_id']

        # Add state field only if supported
        if self._has_state_field():
            fields.append('state')

        # Add date fields only if supported
        if has_date_fields:
            fields.extend([start_field, end_field])

        # Add model-specific fields
        if self.contract_model == 'contract.contract':
            fields.extend(['recurring_next_date', 'recurring_interval', 'recurring_rule_type'])
        elif self.contract_model == 'sale.subscription':
            fields.extend(['recurring_total', 'template_id'])

        try:
            order = f'{end_field} asc' if has_date_fields else 'name asc'
            return self.client.search_read(
                self.contract_model,
                domain,
                fields=fields,
                limit=limit,
                order=order
            )
        except Exception as e:
            logger.error(f"Error searching contracts: {e}")
            # Try simpler search without ordering
            fallback_fields = ['name', 'partner_id']
            if self._has_state_field():
                fallback_fields.append('state')
            return self.client.search_read(
                self.contract_model,
                domain,
                fields=fallback_fields,
                limit=limit
            )

    def get_contract_details(self, contract_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific contract.

        Args:
            contract_id: Odoo contract record ID

        Returns:
            Complete contract details
        """
        contracts = self.client.read(self.contract_model, [contract_id])
        if not contracts:
            return {}

        contract = contracts[0]

        # Get related line items if available
        if self.contract_model == 'contract.contract':
            lines = self.client.search_read(
                'contract.line',
                [['contract_id', '=', contract_id]],
                fields=['name', 'product_id', 'quantity', 'price_unit', 'price_subtotal']
            )
            contract['contract_lines'] = lines

        return contract

    def get_expiring_contracts(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get contracts expiring within specified days.

        Args:
            days: Number of days to look ahead

        Returns:
            List of expiring contracts
        """
        # If model doesn't support date fields, return empty list
        if not self._has_date_fields():
            logger.info(f"Model {self.contract_model} doesn't support date fields, cannot find expiring contracts")
            return []
        return self.search_contracts(expiring_within_days=days)

    def create_contract(
        self,
        name: str,
        partner_id: int,
        date_start: str,
        date_end: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new contract.

        Args:
            name: Contract name/reference
            partner_id: Customer/vendor Odoo ID
            date_start: Start date (YYYY-MM-DD)
            date_end: Optional end date (YYYY-MM-DD)
            **kwargs: Additional fields

        Returns:
            Created contract details with ID
        """
        start_field, end_field = self._get_date_field()

        values = {
            'name': name,
            'partner_id': partner_id,
            start_field: date_start,
        }

        if date_end:
            values[end_field] = date_end

        # Add additional fields
        values.update(kwargs)

        contract_id = self.client.create(self.contract_model, values)

        return {
            'id': contract_id,
            'name': name,
            'partner_id': partner_id,
            'date_start': date_start,
            'date_end': date_end
        }

    def update_contract(
        self,
        contract_id: int,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update an existing contract.

        Args:
            contract_id: Odoo contract ID
            updates: Dictionary of fields to update

        Returns:
            Success status
        """
        return self.client.write(self.contract_model, [contract_id], updates)

    def get_contract_summary(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a contract summary/report.

        Args:
            date_from: Start date for report period
            date_to: End date for report period

        Returns:
            Summary statistics
        """
        summary = {
            'total': 0,
            'by_state': {},
            'expiring_soon': 0,
        }

        try:
            # Count total
            summary['total'] = self.client.search_count(self.contract_model, [])

            # Try to count by state only if model supports it
            if self._has_state_field():
                states = ['draft', 'open', 'close', 'cancelled']
                for state in states:
                    try:
                        count = self.client.search_count(
                            self.contract_model,
                            [['state', '=', state]]
                        )
                        summary['by_state'][state] = count
                    except:
                        summary['by_state'][state] = 0
            else:
                summary['by_state'] = {'note': 'State tracking not available for this model'}

            # Count expiring - only if model supports date fields
            has_date_fields = self._has_date_fields()
            if has_date_fields:
                _, end_field = self._get_date_field()
                end_date = date.today() + timedelta(days=30)
                try:
                    summary['expiring_soon'] = self.client.search_count(
                        self.contract_model,
                        [
                            [end_field, '<=', end_date.isoformat()],
                            [end_field, '>=', date.today().isoformat()],
                        ]
                    )
                except:
                    summary['expiring_soon'] = 0

        except Exception as e:
            logger.error(f"Error getting contract summary: {e}")

        return summary

    def get_partner_contracts(self, partner_id: int) -> List[Dict[str, Any]]:
        """
        Get all contracts for a specific partner.

        Args:
            partner_id: Partner (customer/vendor) ID

        Returns:
            List of contracts for the partner
        """
        return self.client.search_read(
            self.contract_model,
            [['partner_id', '=', partner_id]],
            order='create_date desc'
        )
