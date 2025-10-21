from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from bot.menu_api import MenuAPI

def show_categories(update: Update, context: CallbackContext):
    """Show all categories"""
    query = update.callback_query
    query.answer()
    
    categories = MenuAPI.get_categories()
    
    if not categories:
        query.edit_message_text("No categories available at the moment.")
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
    query.edit_message_text(
        "📂 Select a Category:",
        reply_markup=reply_markup
    )

def handle_category_select(update: Update, context: CallbackContext):
    """Handle category selection"""
    query = update.callback_query
    query.answer()
    
    category_id = query.data.replace("category_", "")
    
    from bot.handlers.products import show_products
    show_products(update, context, category_id)