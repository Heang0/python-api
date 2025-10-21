from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.menu_api import MenuAPI

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all categories"""
    query = update.callback_query
    await query.answer()
    
    categories = MenuAPI.get_categories()
    
    if not categories:
        await query.edit_message_text("No categories available at the moment.")
        return
    
    # Create category buttons (2 per row)
    keyboard = []
    row = []
    for category in categories:
        row.append(InlineKeyboardButton(
            f"📁 {category['name']}", 
            callback_data=f"category_{category['_id']}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:  # Add remaining buttons
        keyboard.append(row)
    
    # Add navigation
    keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "📂 Select a Category:",
        reply_markup=reply_markup
    )

async def handle_category_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection"""
    query = update.callback_query
    await query.answer()
    
    category_id = query.data.replace("category_", "")
    
    from bot.handlers.products import show_products
    await show_products(update, context, category_id)