"""Odoo model-specific operations."""

from .contracts import ContractOperations
from .hr import HROperations
from .finance import FinanceOperations

__all__ = ["ContractOperations", "HROperations", "FinanceOperations"]
