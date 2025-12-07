"""Odoo ERP integration via XML-RPC."""

from .client import OdooClient, get_odoo_client

__all__ = ["OdooClient", "get_odoo_client"]
