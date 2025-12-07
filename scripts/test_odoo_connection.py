"""
Test Odoo Connection and Discover Modules

Run this script to verify Odoo connectivity and discover installed modules.
Usage: python scripts/test_odoo_connection.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.integrations.odoo.client import OdooClient, OdooConfig
from src.core.logging import setup_logging, get_logger

setup_logging(level="INFO")
logger = get_logger(__name__)


def main():
    """Test Odoo connection and discover modules."""
    print("=" * 60)
    print("Odoo Connection Test")
    print("=" * 60)

    # Create client with settings
    config = OdooConfig(
        url=settings.odoo_url,
        database=settings.odoo_db,
        username=settings.odoo_username,
        password=settings.odoo_password,
        timeout=settings.odoo_timeout
    )

    print(f"\nConnecting to: {config.url}")
    print(f"Database: {config.database}")
    print(f"Username: {config.username}")

    client = OdooClient(config)

    # Test authentication
    print("\n1. Testing Authentication...")
    try:
        uid = client.authenticate()
        print(f"   SUCCESS: Authenticated as user ID: {uid}")
    except Exception as e:
        print(f"   FAILED: {e}")
        return

    # Get version info
    print("\n2. Odoo Version Info...")
    try:
        version = client.get_version()
        print(f"   Server Version: {version.get('server_version', 'Unknown')}")
        print(f"   Protocol Version: {version.get('protocol_version', 'Unknown')}")
    except Exception as e:
        print(f"   Error getting version: {e}")

    # Discover contract-related modules
    print("\n3. Contract-related Modules...")
    try:
        contract_modules = client.get_installed_modules(name_filter='contract')
        if contract_modules:
            for mod in contract_modules:
                print(f"   - {mod['name']}: {mod.get('shortdesc', 'No description')}")
        else:
            print("   No contract modules found")

        # Check for subscription module
        subscription_modules = client.get_installed_modules(name_filter='subscription')
        if subscription_modules:
            print("\n   Subscription Modules:")
            for mod in subscription_modules:
                print(f"   - {mod['name']}: {mod.get('shortdesc', 'No description')}")
    except Exception as e:
        print(f"   Error: {e}")

    # Discover HR modules
    print("\n4. HR-related Modules...")
    try:
        hr_modules = client.get_installed_modules(name_filter='hr')
        if hr_modules:
            for mod in hr_modules[:10]:  # Limit to first 10
                print(f"   - {mod['name']}: {mod.get('shortdesc', 'No description')}")
            if len(hr_modules) > 10:
                print(f"   ... and {len(hr_modules) - 10} more")
        else:
            print("   No HR modules found")
    except Exception as e:
        print(f"   Error: {e}")

    # Check available models
    print("\n5. Available Models for Contracts...")
    try:
        contract_models = ['contract.contract', 'sale.subscription', 'sale.order']
        for model in contract_models:
            exists = client.check_model_exists(model)
            status = "AVAILABLE" if exists else "not found"
            print(f"   - {model}: {status}")
    except Exception as e:
        print(f"   Error: {e}")

    print("\n6. Available Models for HR...")
    try:
        hr_models = [
            'hr.employee', 'hr.department', 'hr.job',
            'hr.contract', 'hr.leave', 'hr.leave.type',
            'hr.applicant', 'hr.attendance'
        ]
        for model in hr_models:
            exists = client.check_model_exists(model)
            status = "AVAILABLE" if exists else "not found"
            print(f"   - {model}: {status}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test a simple query
    print("\n7. Sample Data Test...")
    try:
        # Get a few partners
        partners = client.search_read(
            'res.partner',
            [['is_company', '=', True]],
            fields=['name', 'email'],
            limit=3
        )
        print(f"   Found {len(partners)} sample companies")
        for p in partners:
            print(f"   - {p['name']}")
    except Exception as e:
        print(f"   Error: {e}")

    print("\n" + "=" * 60)
    print("Connection Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
