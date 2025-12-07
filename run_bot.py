"""
Simple Telegram Bot Runner
Run this file directly: python run_bot.py
"""

import asyncio
import os
import sys

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Get token from environment
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Simple in-memory storage for conversations
user_threads = {}

def get_thread_id(user_id):
    import secrets
    if user_id not in user_threads:
        user_threads[user_id] = secrets.token_hex(16)
    return user_threads[user_id]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Enterprise Agent System*\n\n"
        "I can help you with:\n"
        "• /contracts - Contract management\n"
        "• /hr - HR operations\n"
        "• /status - Check system status\n\n"
        "Just type your question!",
        parse_mode="Markdown"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Commands:*\n"
        "/start - Welcome\n"
        "/contracts - Contracts menu\n"
        "/hr - HR menu\n"
        "/status - System status\n"
        "/new - New conversation\n\n"
        "*Try asking:*\n"
        "• Show expiring contracts\n"
        "• List employees\n"
        "• Pending leave requests",
        parse_mode="Markdown"
    )


async def contracts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Expiring Soon", callback_data="q:Show contracts expiring in the next 30 days")],
        [InlineKeyboardButton("📋 All Contracts", callback_data="q:List all active contracts")],
        [InlineKeyboardButton("📊 Summary", callback_data="q:Give me a contract summary report")]
    ]
    await update.message.reply_text(
        "📄 *Contract Management*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def hr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⏳ Pending Leaves", callback_data="q:Show pending leave requests")],
        [InlineKeyboardButton("👥 Employees", callback_data="q:List all employees")],
        [InlineKeyboardButton("🏢 Departments", callback_data="q:Show all departments")]
    ]
    await update.message.reply_text(
        "👔 *HR Operations*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check Odoo
    odoo_status = "🔴 Error"
    try:
        from src.integrations.odoo.client import get_odoo_client
        client = get_odoo_client()
        client.authenticate()
        v = client.get_version()
        odoo_status = f"🟢 v{v.get('server_version', '?')}"
    except Exception as e:
        odoo_status = f"🔴 {str(e)[:30]}"

    await update.message.reply_text(
        f"📊 *System Status*\n\n"
        f"🤖 Agents: 🟢 Ready\n"
        f"🗄️ Odoo: {odoo_status}\n"
        f"🧠 Gemini: {'🟢 Configured' if GOOGLE_API_KEY else '🔴 Missing'}",
        parse_mode="Markdown"
    )


async def new_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    import secrets
    user_threads[user_id] = secrets.token_hex(16)
    await update.message.reply_text("🔄 Started new conversation!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process user message with the agent system."""
    user_id = update.effective_user.id
    text = update.message.text

    await update.message.chat.send_action("typing")

    try:
        from src.agents.supervisor import invoke_agent, get_last_ai_message

        thread_id = get_thread_id(user_id)

        print(f"[{user_id}] Processing: {text[:50]}...")

        result = await invoke_agent(
            message=text,
            thread_id=thread_id,
            user_context={"user_id": str(user_id), "telegram_id": user_id}
        )

        response = get_last_ai_message(result)
        print(f"[{user_id}] Response: {response[:100]}...")

        # Split long messages
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await update.message.reply_text(response[i:i+4000])
        else:
            await update.message.reply_text(response)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}\n\nTry /new to start fresh.")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id

    if data.startswith("q:"):
        question = data[2:]
        await query.edit_message_text(f"⏳ Processing: {question}...")

        try:
            from src.agents.supervisor import invoke_agent, get_last_ai_message

            result = await invoke_agent(
                message=question,
                thread_id=get_thread_id(user_id),
                user_context={"user_id": str(user_id)}
            )

            response = get_last_ai_message(result)

            if len(response) > 4000:
                response = response[:4000] + "..."

            await query.edit_message_text(response)

        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)[:200]}")


async def delete_webhook():
    """Delete any existing webhook before starting polling."""
    from telegram import Bot
    bot = Bot(token=BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    print("✓ Webhook deleted (polling mode enabled)")


def main():
    print("=" * 50)
    print("Enterprise Agent Telegram Bot")
    print("=" * 50)

    if not BOT_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not found in .env")
        print("Add it to your .env file")
        return

    print(f"✓ Bot token: {BOT_TOKEN[:20]}...")
    print(f"✓ Google API: {'Configured' if GOOGLE_API_KEY else 'MISSING!'}")

    # Delete any existing webhook first
    asyncio.run(delete_webhook())

    # Test Odoo connection
    try:
        from src.integrations.odoo.client import get_odoo_client
        client = get_odoo_client()
        client.authenticate()
        print(f"✓ Odoo: Connected")
    except Exception as e:
        print(f"⚠ Odoo: {e}")

    print("\n🚀 Starting bot (polling mode)...")
    print("Send a message to your bot on Telegram!")
    print("Press Ctrl+C to stop\n")

    # Build and run
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("contracts", contracts_cmd))
    app.add_handler(CommandHandler("hr", hr_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("new", new_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
