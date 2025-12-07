"""
Notification Service

Handles sending notifications via various channels (Telegram, email, etc.).
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for sending notifications through various channels.
    """

    def __init__(self):
        self._pending_notifications: List[Dict[str, Any]] = []

    async def send_telegram_message(
        self,
        chat_id: int,
        message: str
    ) -> bool:
        """
        Send a message via Telegram.

        Args:
            chat_id: Telegram chat ID
            message: Message to send

        Returns:
            Success status
        """
        try:
            from src.integrations.telegram.bot import get_bot_manager
            bot_manager = get_bot_manager()

            if bot_manager.application:
                await bot_manager.application.bot.send_message(
                    chat_id=chat_id,
                    text=message
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def send_contract_expiry_alert(
        self,
        contract_id: int,
        contract_name: str,
        days_until_expiry: int,
        recipients: List[int]
    ) -> None:
        """
        Send contract expiry alert to recipients.

        Args:
            contract_id: Contract ID
            contract_name: Contract name
            days_until_expiry: Days until expiration
            recipients: List of Telegram chat IDs
        """
        urgency = "CRITICAL" if days_until_expiry <= 7 else "URGENT"
        message = (
            f"Contract Expiry Alert ({urgency})\n\n"
            f"Contract: {contract_name} (ID: {contract_id})\n"
            f"Expires in: {days_until_expiry} days\n\n"
            f"Please review and take appropriate action."
        )

        for chat_id in recipients:
            await self.send_telegram_message(chat_id, message)

    async def send_leave_approval_notification(
        self,
        employee_name: str,
        leave_type: str,
        date_from: str,
        date_to: str,
        approved: bool,
        recipient_chat_id: int
    ) -> None:
        """
        Send leave approval/rejection notification.

        Args:
            employee_name: Employee name
            leave_type: Type of leave
            date_from: Start date
            date_to: End date
            approved: Whether approved or rejected
            recipient_chat_id: Telegram chat ID
        """
        status = "APPROVED" if approved else "REJECTED"
        emoji = "" if approved else ""

        message = (
            f"Leave Request {status} {emoji}\n\n"
            f"Employee: {employee_name}\n"
            f"Type: {leave_type}\n"
            f"Period: {date_from} to {date_to}"
        )

        await self.send_telegram_message(recipient_chat_id, message)

    def queue_notification(
        self,
        notification_type: str,
        data: Dict[str, Any],
        scheduled_for: Optional[datetime] = None
    ) -> str:
        """
        Queue a notification for later sending.

        Args:
            notification_type: Type of notification
            data: Notification data
            scheduled_for: Optional scheduled time

        Returns:
            Notification ID
        """
        import uuid
        notification_id = str(uuid.uuid4())

        self._pending_notifications.append({
            "id": notification_id,
            "type": notification_type,
            "data": data,
            "scheduled_for": scheduled_for or datetime.utcnow(),
            "created_at": datetime.utcnow()
        })

        return notification_id

    def get_pending_notifications(self) -> List[Dict[str, Any]]:
        """Get all pending notifications."""
        return self._pending_notifications.copy()


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
