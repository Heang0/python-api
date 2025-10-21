from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message and show main menu"""
    store_name = "YSG Store"  # You can fetch this from API
    
    keyboard = [
        [InlineKeyboardButton("📂 Categories", callback_data="categories")],
        [InlineKeyboardButton("🍽️ All Products", callback_data="category_all")],
        [InlineKeyboardButton("🏪 Store Info", callback_data="store_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(
            f"Welcome to {store_name}! 🍕\nBrowse our menu:",
            reply_markup=reply_markup
        )
    else:
        await update.callback_query.edit_message_text(
            f"Welcome to {store_name}! 🍕\nBrowse our menu:",
            reply_markup=reply_markup
        )