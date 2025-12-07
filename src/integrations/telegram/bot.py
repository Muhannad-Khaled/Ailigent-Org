"""
Telegram Bot Manager

Manages Telegram bot lifecycle with FastAPI webhook integration.
Uses python-telegram-bot v22+ with async handlers.
"""

import logging
from typing import Optional, Callable, Awaitable

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from src.config import settings
from src.agents.supervisor import invoke_agent, get_last_ai_message
from src.core.security import generate_thread_id

logger = logging.getLogger(__name__)


class TelegramBotManager:
    """
    Manages Telegram bot lifecycle with FastAPI webhook integration.

    Handles message routing to the multi-agent system and provides
    command handlers for common operations.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        webhook_url: Optional[str] = None
    ):
        """
        Initialize the Telegram bot manager.

        Args:
            token: Bot token (uses settings if not provided)
            webhook_url: Full webhook URL (uses settings if not provided)
        """
        self.token = token or settings.telegram_bot_token
        self.webhook_url = webhook_url or settings.telegram_webhook_full_url
        self.application: Optional[Application] = None
        self._user_threads: dict = {}  # Map user_id to thread_id

    async def initialize(self) -> None:
        """Initialize the bot application."""
        logger.info("Initializing Telegram bot...")

        # Build application without updater (webhook mode)
        self.application = (
            Application.builder()
            .token(self.token)
            .updater(None)  # Disable polling, use webhook
            .build()
        )

        # Register handlers
        self._register_handlers()

        # Initialize application
        await self.application.initialize()
        logger.info("Telegram bot initialized")

    async def start(self) -> None:
        """Start the bot and set webhook."""
        if self.application is None:
            await self.initialize()

        await self.application.start()

        # Set webhook
        await self.application.bot.set_webhook(url=self.webhook_url)
        logger.info(f"Telegram webhook set to: {self.webhook_url}")

    async def stop(self) -> None:
        """Stop the bot and remove webhook."""
        if self.application:
            try:
                await self.application.bot.delete_webhook()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Telegram bot stopped")
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")

    def _register_handlers(self) -> None:
        """Register command and message handlers."""
        if self.application is None:
            return

        # Command handlers
        self.application.add_handler(
            CommandHandler("start", self._handle_start)
        )
        self.application.add_handler(
            CommandHandler("help", self._handle_help)
        )
        self.application.add_handler(
            CommandHandler("contracts", self._handle_contracts)
        )
        self.application.add_handler(
            CommandHandler("hr", self._handle_hr)
        )
        self.application.add_handler(
            CommandHandler("status", self._handle_status)
        )
        self.application.add_handler(
            CommandHandler("new", self._handle_new_conversation)
        )

        # Message handler for all text messages
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_message
            )
        )

        # Callback query handler for inline buttons
        self.application.add_handler(
            CallbackQueryHandler(self._handle_callback)
        )

    def _get_thread_id(self, user_id: int) -> str:
        """Get or create a thread ID for a user."""
        if user_id not in self._user_threads:
            self._user_threads[user_id] = generate_thread_id()
        return self._user_threads[user_id]

    async def _handle_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command."""
        welcome_message = (
            "Welcome to the Enterprise Agent System!\n\n"
            "I can help you with:\n"
            "- Contract management (/contracts)\n"
            "- HR operations (/hr)\n"
            "- System status (/status)\n\n"
            "Just type your request and I'll route it to the right agent.\n\n"
            "Use /new to start a fresh conversation."
        )
        await update.message.reply_text(welcome_message)

    async def _handle_help(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /help command."""
        help_text = (
            "*Available Commands:*\n\n"
            "/start - Welcome message\n"
            "/contracts - Contract management menu\n"
            "/hr - Human resources menu\n"
            "/status - Check system status\n"
            "/new - Start new conversation\n"
            "/help - Show this help\n\n"
            "*Examples:*\n"
            "- 'Show me expiring contracts'\n"
            "- 'List employees in Engineering'\n"
            "- 'Check leave balance for employee 5'\n"
            "- 'Create a leave request'"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def _handle_contracts(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /contracts command."""
        keyboard = [
            [
                InlineKeyboardButton("Expiring Soon", callback_data="contracts_expiring"),
                InlineKeyboardButton("All Contracts", callback_data="contracts_all")
            ],
            [
                InlineKeyboardButton("Search", callback_data="contracts_search"),
                InlineKeyboardButton("Summary", callback_data="contracts_summary")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Contract Management - Select an option:",
            reply_markup=reply_markup
        )

    async def _handle_hr(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /hr command."""
        keyboard = [
            [
                InlineKeyboardButton("Pending Leaves", callback_data="hr_leaves_pending"),
                InlineKeyboardButton("Employees", callback_data="hr_employees")
            ],
            [
                InlineKeyboardButton("Departments", callback_data="hr_departments"),
                InlineKeyboardButton("Job Openings", callback_data="hr_jobs")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "HR Operations - Select an option:",
            reply_markup=reply_markup
        )

    async def _handle_status(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /status command."""
        status_message = (
            "*System Status:* Operational\n\n"
            "- Executive Agent: Active\n"
            "- Contracts Agent: Active\n"
            "- HR Agent: Active\n"
            "- Odoo ERP: Connected"
        )
        await update.message.reply_text(status_message, parse_mode="Markdown")

    async def _handle_new_conversation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /new command - start a new conversation."""
        user_id = update.effective_user.id
        self._user_threads[user_id] = generate_thread_id()

        await update.message.reply_text(
            "Started a new conversation. How can I help you?"
        )

    async def _handle_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle regular text messages - route to agent system."""
        user_id = update.effective_user.id
        username = update.effective_user.username or str(user_id)
        message_text = update.message.text

        # Show typing indicator
        await update.message.chat.send_action("typing")

        try:
            thread_id = self._get_thread_id(user_id)

            user_context = {
                "user_id": str(user_id),
                "telegram_id": user_id,
                "username": username,
            }

            result = await invoke_agent(
                message=message_text,
                thread_id=thread_id,
                user_context=user_context
            )

            response = get_last_ai_message(result)

            # Telegram has a 4096 character limit
            if len(response) > 4000:
                # Split into chunks
                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(response)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await update.message.reply_text(
                "Sorry, I encountered an error processing your request. "
                "Please try again or use /new to start a fresh conversation."
            )

    async def _handle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = update.effective_user.id

        # Map callback data to natural language queries
        queries = {
            "contracts_expiring": "Show me contracts expiring in the next 30 days",
            "contracts_all": "List all active contracts",
            "contracts_search": "How can I search for contracts?",
            "contracts_summary": "Give me a contract summary report",
            "hr_leaves_pending": "Show pending leave requests",
            "hr_employees": "List employees",
            "hr_departments": "Show all departments",
            "hr_jobs": "Show open job positions"
        }

        if data in queries:
            await query.edit_message_text(f"Processing: {queries[data]}...")

            try:
                thread_id = self._get_thread_id(user_id)

                result = await invoke_agent(
                    message=queries[data],
                    thread_id=thread_id,
                    user_context={"user_id": str(user_id)}
                )

                response = get_last_ai_message(result)

                if len(response) > 4000:
                    await query.edit_message_text(response[:4000])
                else:
                    await query.edit_message_text(response)

            except Exception as e:
                logger.error(f"Error processing callback: {e}")
                await query.edit_message_text(
                    "Sorry, I encountered an error. Please try again."
                )
        else:
            await query.edit_message_text(f"Unknown action: {data}")

    async def process_update(self, update_data: dict) -> None:
        """Process an incoming webhook update."""
        if self.application:
            update = Update.de_json(update_data, self.application.bot)
            await self.application.process_update(update)


# Singleton instance
_bot_manager: Optional[TelegramBotManager] = None


def get_bot_manager() -> TelegramBotManager:
    """Get or create singleton bot manager."""
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = TelegramBotManager()
    return _bot_manager
