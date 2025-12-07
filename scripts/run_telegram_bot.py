"""
Run Telegram Bot in Polling Mode (for local development)

This script runs the Telegram bot using polling instead of webhooks,
which works without a public URL.

Usage: python scripts/run_telegram_bot.py
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
from src.core.logging import setup_logging, get_logger
from src.core.security import generate_thread_id

setup_logging(level="INFO")
logger = get_logger(__name__)

# Store user thread IDs
user_threads = {}


def get_thread_id(user_id: int) -> str:
    """Get or create a thread ID for a user."""
    if user_id not in user_threads:
        user_threads[user_id] = generate_thread_id()
    return user_threads[user_id]


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    welcome = (
        "🤖 Welcome to the Enterprise Agent System!\n\n"
        "I can help you with:\n"
        "• /contracts - Contract management\n"
        "• /hr - HR operations\n"
        "• /status - System status\n"
        "• /new - Start new conversation\n\n"
        "Just type your question and I'll help!"
    )
    await update.message.reply_text(welcome)


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        "📋 *Available Commands:*\n\n"
        "/start - Welcome message\n"
        "/contracts - Contract menu\n"
        "/hr - HR menu\n"
        "/status - System status\n"
        "/new - New conversation\n"
        "/help - This help\n\n"
        "*Examples:*\n"
        "• Show expiring contracts\n"
        "• List employees in Sales\n"
        "• Check leave balance for employee 5"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def handle_contracts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /contracts command."""
    keyboard = [
        [
            InlineKeyboardButton("📅 Expiring Soon", callback_data="contracts_expiring"),
            InlineKeyboardButton("📋 All Contracts", callback_data="contracts_all")
        ],
        [
            InlineKeyboardButton("📊 Summary", callback_data="contracts_summary")
        ]
    ]
    await update.message.reply_text(
        "📄 *Contract Management*\nSelect an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def handle_hr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /hr command."""
    keyboard = [
        [
            InlineKeyboardButton("⏳ Pending Leaves", callback_data="hr_leaves"),
            InlineKeyboardButton("👥 Employees", callback_data="hr_employees")
        ],
        [
            InlineKeyboardButton("🏢 Departments", callback_data="hr_departments"),
            InlineKeyboardButton("💼 Job Openings", callback_data="hr_jobs")
        ]
    ]
    await update.message.reply_text(
        "👔 *HR Operations*\nSelect an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    # Check Odoo connection
    odoo_status = "🔴 Disconnected"
    try:
        from src.integrations.odoo.client import get_odoo_client
        client = get_odoo_client()
        client.authenticate()
        version = client.get_version()
        odoo_status = f"🟢 Connected (v{version.get('server_version', '?')})"
    except Exception as e:
        odoo_status = f"🔴 Error: {str(e)[:30]}"

    status = (
        "📊 *System Status*\n\n"
        f"🤖 Executive Agent: 🟢 Active\n"
        f"📄 Contracts Agent: 🟢 Active\n"
        f"👔 HR Agent: 🟢 Active\n"
        f"🗄️ Odoo ERP: {odoo_status}"
    )
    await update.message.reply_text(status, parse_mode="Markdown")


async def handle_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /new command."""
    user_id = update.effective_user.id
    user_threads[user_id] = generate_thread_id()
    await update.message.reply_text("🔄 Started new conversation. How can I help?")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages - route to agent system."""
    user_id = update.effective_user.id
    message_text = update.message.text

    # Show typing indicator
    await update.message.chat.send_action("typing")

    try:
        # Import and invoke agent
        from src.agents.supervisor import invoke_agent, get_last_ai_message

        thread_id = get_thread_id(user_id)
        user_context = {
            "user_id": str(user_id),
            "telegram_id": user_id,
            "username": update.effective_user.username or str(user_id),
        }

        logger.info(f"Processing message from {user_id}: {message_text[:50]}...")

        result = await invoke_agent(
            message=message_text,
            thread_id=thread_id,
            user_context=user_context
        )

        response = get_last_ai_message(result)

        # Telegram has 4096 char limit
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await update.message.reply_text(response[i:i+4000])
        else:
            await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Sorry, an error occurred: {str(e)[:100]}\n\n"
            "Try /new to start a fresh conversation."
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    # Map callbacks to queries
    queries = {
        "contracts_expiring": "Show me contracts expiring in the next 30 days",
        "contracts_all": "List all active contracts",
        "contracts_summary": "Give me a contract summary report",
        "hr_leaves": "Show pending leave requests",
        "hr_employees": "List all employees",
        "hr_departments": "Show all departments",
        "hr_jobs": "Show open job positions"
    }

    if data in queries:
        await query.edit_message_text(f"⏳ Processing: {queries[data]}...")

        try:
            from src.agents.supervisor import invoke_agent, get_last_ai_message

            result = await invoke_agent(
                message=queries[data],
                thread_id=get_thread_id(user_id),
                user_context={"user_id": str(user_id)}
            )

            response = get_last_ai_message(result)
            if len(response) > 4000:
                response = response[:4000] + "..."

            await query.edit_message_text(response)

        except Exception as e:
            logger.error(f"Callback error: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)[:100]}")


def main():
    """Run the bot in polling mode."""
    print("=" * 60)
    print("Enterprise Agent Telegram Bot")
    print("=" * 60)

    if not settings.telegram_bot_token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        return

    print(f"✓ Bot token configured")
    print(f"✓ Odoo URL: {settings.odoo_url}")
    print(f"✓ Using Gemini model: {settings.gemini_model}")
    print("\n🚀 Starting bot in polling mode...")
    print("Press Ctrl+C to stop\n")

    # Build application
    app = Application.builder().token(settings.telegram_bot_token).build()

    # Add handlers
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(CommandHandler("contracts", handle_contracts))
    app.add_handler(CommandHandler("hr", handle_hr))
    app.add_handler(CommandHandler("status", handle_status))
    app.add_handler(CommandHandler("new", handle_new))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Run with polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
