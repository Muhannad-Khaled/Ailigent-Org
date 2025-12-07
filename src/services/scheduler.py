"""
Background Task Scheduler

Handles scheduled tasks like contract expiry checks and notifications.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    Background task scheduler for periodic operations.
    """

    def __init__(self):
        self._running = False
        self._tasks = []

    async def start(self):
        """Start the scheduler."""
        self._running = True
        logger.info("Task scheduler started")

        # Schedule periodic tasks
        self._tasks = [
            asyncio.create_task(self._check_expiring_contracts()),
            asyncio.create_task(self._check_pending_leaves()),
        ]

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        logger.info("Task scheduler stopped")

    async def _check_expiring_contracts(self):
        """Periodic task to check for expiring contracts."""
        while self._running:
            try:
                logger.debug("Checking for expiring contracts...")

                from src.integrations.odoo.client import get_odoo_client
                from src.integrations.odoo.models.contracts import ContractOperations

                client = get_odoo_client()
                ops = ContractOperations(client)

                # Check contracts expiring in next 7 days
                expiring = ops.get_expiring_contracts(days=7)

                if expiring:
                    logger.info(f"Found {len(expiring)} contracts expiring in 7 days")
                    # Could trigger notifications here

            except Exception as e:
                logger.error(f"Error checking expiring contracts: {e}")

            # Run every hour
            await asyncio.sleep(3600)

    async def _check_pending_leaves(self):
        """Periodic task to check for pending leave requests."""
        while self._running:
            try:
                logger.debug("Checking for pending leave requests...")

                from src.integrations.odoo.client import get_odoo_client
                from src.integrations.odoo.models.hr import HROperations

                client = get_odoo_client()
                ops = HROperations(client)

                pending = ops.get_pending_leave_requests()

                if pending:
                    logger.info(f"Found {len(pending)} pending leave requests")
                    # Could trigger notifications here

            except Exception as e:
                logger.error(f"Error checking pending leaves: {e}")

            # Run every 30 minutes
            await asyncio.sleep(1800)


# Entry point for running as standalone worker
async def main():
    """Main entry point for scheduler worker."""
    from src.core.logging import setup_logging
    from src.config import settings

    setup_logging(level=settings.log_level)
    logger.info("Starting scheduler worker...")

    scheduler = TaskScheduler()
    await scheduler.start()

    try:
        # Keep running
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
