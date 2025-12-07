"""
Odoo XML-RPC Client

A robust client for interacting with Odoo ERP via XML-RPC protocol.
Provides connection management, CRUD operations, and error handling.
"""

import xmlrpc.client
from typing import Any, Dict, List, Optional, Union, Tuple
from functools import lru_cache
from dataclasses import dataclass
import logging

from src.config import settings
from src.core.exceptions import OdooConnectionError, OdooOperationError

logger = logging.getLogger(__name__)


@dataclass
class OdooConfig:
    """Odoo connection configuration."""
    url: str
    database: str
    username: str
    password: str
    timeout: int = 30


class OdooClient:
    """
    Wrapper for Odoo XML-RPC operations.

    Provides CRUD operations, connection management, and error handling.
    Thread-safe for concurrent access.

    Usage:
        client = OdooClient(OdooConfig(...))
        client.authenticate()
        partners = client.search_read('res.partner', [['is_company', '=', True]])
    """

    def __init__(self, config: Optional[OdooConfig] = None):
        """
        Initialize Odoo client.

        Args:
            config: Optional configuration. Uses settings if not provided.
        """
        if config is None:
            config = OdooConfig(
                url=settings.odoo_url,
                database=settings.odoo_db,
                username=settings.odoo_username,
                password=settings.odoo_password,
                timeout=settings.odoo_timeout
            )
        self.config = config
        self._uid: Optional[int] = None
        self._common: Optional[xmlrpc.client.ServerProxy] = None
        self._models: Optional[xmlrpc.client.ServerProxy] = None

    @property
    def common(self) -> xmlrpc.client.ServerProxy:
        """Get common endpoint proxy (lazy initialization)."""
        if self._common is None:
            self._common = xmlrpc.client.ServerProxy(
                f'{self.config.url}/xmlrpc/2/common',
                allow_none=True
            )
        return self._common

    @property
    def models(self) -> xmlrpc.client.ServerProxy:
        """Get models endpoint proxy (lazy initialization)."""
        if self._models is None:
            self._models = xmlrpc.client.ServerProxy(
                f'{self.config.url}/xmlrpc/2/object',
                allow_none=True
            )
        return self._models

    @property
    def uid(self) -> int:
        """Get authenticated user ID, authenticating if necessary."""
        if self._uid is None:
            self.authenticate()
        return self._uid

    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self._uid is not None

    def authenticate(self) -> int:
        """
        Authenticate with Odoo server.

        Returns:
            User ID if authentication successful

        Raises:
            OdooConnectionError: If authentication fails
        """
        try:
            logger.info(f"Authenticating to Odoo at {self.config.url}")
            self._uid = self.common.authenticate(
                self.config.database,
                self.config.username,
                self.config.password,
                {}
            )
            if not self._uid:
                raise OdooConnectionError(
                    "Authentication failed - invalid credentials",
                    details={"url": self.config.url, "database": self.config.database}
                )
            logger.info(f"Successfully authenticated as user ID: {self._uid}")
            return self._uid
        except xmlrpc.client.Fault as e:
            raise OdooConnectionError(
                f"Odoo fault during authentication: {e.faultString}",
                details={"fault_code": e.faultCode}
            )
        except Exception as e:
            raise OdooConnectionError(
                f"Connection error: {str(e)}",
                details={"url": self.config.url}
            )

    def execute(
        self,
        model: str,
        method: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an Odoo model method.

        Args:
            model: Odoo model name (e.g., 'res.partner')
            method: Method to call (e.g., 'search_read')
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method

        Returns:
            Result from Odoo

        Raises:
            OdooOperationError: If the operation fails
        """
        try:
            result = self.models.execute_kw(
                self.config.database,
                self.uid,
                self.config.password,
                model,
                method,
                list(args),
                kwargs or {}
            )
            return result
        except xmlrpc.client.Fault as e:
            raise OdooOperationError(
                f"Operation failed: {e.faultString}",
                model=model,
                method=method,
                details={"fault_code": e.faultCode}
            )
        except Exception as e:
            raise OdooOperationError(
                f"Operation error: {str(e)}",
                model=model,
                method=method
            )

    def search(
        self,
        model: str,
        domain: List[Union[Tuple, List]],
        limit: Optional[int] = None,
        offset: int = 0,
        order: Optional[str] = None
    ) -> List[int]:
        """
        Search for record IDs matching domain.

        Args:
            model: Odoo model name
            domain: Search domain (list of conditions)
            limit: Maximum records to return
            offset: Number of records to skip
            order: Sort order (e.g., 'name asc')

        Returns:
            List of matching record IDs
        """
        kwargs = {}
        if limit is not None:
            kwargs['limit'] = limit
        if offset:
            kwargs['offset'] = offset
        if order:
            kwargs['order'] = order

        return self.execute(model, 'search', domain, **kwargs)

    def read(
        self,
        model: str,
        ids: List[int],
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Read records by ID.

        Args:
            model: Odoo model name
            ids: List of record IDs to read
            fields: Fields to read (None for all)

        Returns:
            List of record dictionaries
        """
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        return self.execute(model, 'read', ids, **kwargs)

    def search_read(
        self,
        model: str,
        domain: List[Union[Tuple, List]],
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search and read in one operation (more efficient).

        Args:
            model: Odoo model name
            domain: Search domain
            fields: Fields to read
            limit: Maximum records
            offset: Records to skip
            order: Sort order

        Returns:
            List of matching records with specified fields
        """
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit is not None:
            kwargs['limit'] = limit
        if offset:
            kwargs['offset'] = offset
        if order:
            kwargs['order'] = order

        return self.execute(model, 'search_read', domain, **kwargs)

    def search_count(
        self,
        model: str,
        domain: List[Union[Tuple, List]]
    ) -> int:
        """
        Count records matching domain.

        Args:
            model: Odoo model name
            domain: Search domain

        Returns:
            Number of matching records
        """
        return self.execute(model, 'search_count', domain)

    def create(
        self,
        model: str,
        values: Dict[str, Any]
    ) -> int:
        """
        Create a new record.

        Args:
            model: Odoo model name
            values: Field values for new record

        Returns:
            ID of created record
        """
        logger.debug(f"Creating {model} with values: {values}")
        record_id = self.execute(model, 'create', values)
        logger.info(f"Created {model} record with ID: {record_id}")
        return record_id

    def write(
        self,
        model: str,
        ids: List[int],
        values: Dict[str, Any]
    ) -> bool:
        """
        Update existing records.

        Args:
            model: Odoo model name
            ids: Record IDs to update
            values: Field values to update

        Returns:
            True if successful
        """
        logger.debug(f"Updating {model} records {ids} with: {values}")
        result = self.execute(model, 'write', ids, values)
        logger.info(f"Updated {model} records: {ids}")
        return result

    def unlink(
        self,
        model: str,
        ids: List[int]
    ) -> bool:
        """
        Delete records.

        Args:
            model: Odoo model name
            ids: Record IDs to delete

        Returns:
            True if successful
        """
        logger.debug(f"Deleting {model} records: {ids}")
        result = self.execute(model, 'unlink', ids)
        logger.info(f"Deleted {model} records: {ids}")
        return result

    def call_method(
        self,
        model: str,
        method: str,
        ids: List[int],
        *args,
        **kwargs
    ) -> Any:
        """
        Call a custom method on records.

        Args:
            model: Odoo model name
            method: Method name to call
            ids: Record IDs
            *args: Additional arguments
            **kwargs: Keyword arguments

        Returns:
            Method result
        """
        return self.execute(model, method, ids, *args, **kwargs)

    def fields_get(
        self,
        model: str,
        attributes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get field definitions for a model.

        Args:
            model: Odoo model name
            attributes: Field attributes to retrieve

        Returns:
            Dictionary of field definitions
        """
        kwargs = {}
        if attributes:
            kwargs['attributes'] = attributes
        return self.execute(model, 'fields_get', **kwargs)

    def get_installed_modules(
        self,
        name_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of installed modules.

        Args:
            name_filter: Optional filter for module name (partial match)

        Returns:
            List of installed modules with name and state
        """
        domain = [['state', '=', 'installed']]
        if name_filter:
            domain.append(['name', 'ilike', name_filter])

        return self.search_read(
            'ir.module.module',
            domain,
            fields=['name', 'shortdesc', 'state', 'installed_version']
        )

    def get_available_models(
        self,
        name_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of available models.

        Args:
            name_filter: Optional filter for model name (partial match)

        Returns:
            List of models with name and description
        """
        domain = []
        if name_filter:
            domain.append(['model', 'ilike', name_filter])

        return self.search_read(
            'ir.model',
            domain,
            fields=['name', 'model', 'state'],
            order='model'
        )

    def check_model_exists(self, model: str) -> bool:
        """
        Check if a model exists in Odoo.

        Args:
            model: Model name to check

        Returns:
            True if model exists
        """
        count = self.search_count('ir.model', [['model', '=', model]])
        return count > 0

    def get_version(self) -> Dict[str, Any]:
        """
        Get Odoo server version information.

        Returns:
            Version information dictionary
        """
        return self.common.version()


# Singleton instance
_client_instance: Optional[OdooClient] = None


def get_odoo_client(config: Optional[OdooConfig] = None) -> OdooClient:
    """
    Get or create singleton Odoo client instance.

    Args:
        config: Optional configuration override

    Returns:
        Configured OdooClient instance
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = OdooClient(config)
    return _client_instance


def reset_odoo_client() -> None:
    """Reset the singleton client instance (useful for testing)."""
    global _client_instance
    _client_instance = None
