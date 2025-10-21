from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from bot.menu_api import MenuAPI

def show_products(update: Update, context: CallbackContext, category_id=None):
    """Show products in a category"""
    query = update.callback_query
    query.answer()
    
    products = MenuAPI.get_products(category_id)
    
    if not products:
        query.edit_message_text("No products found in this category.")
        return
    
    # Get category name for title
    if category_id == "all":
        title = "🍽️ All Products"
    else:
        categories = MenuAPI.get_categories()
        category_name = "Products"
        if categories and category_id != "all":
            for cat in categories:
                if cat['_id'] == category_id:
                    category_name = cat['name']
                    break
        title = f"📁 {category_name}"
    
    # Format products message
    message = f"*{title}*\n\n"
    
    for i, product in enumerate(products, 1):
        price = product.get('price', 'N/A')
        message += f"*{i}. {product['title']}* - `{price}`\n"
        if product.get('description'):
            # Truncate long descriptions
            desc = product['description']
            if len(desc) > 100:
                desc = desc[:100] + "..."
            message += f"   _{desc}_\n"
        message += "\n"
    
    # Navigation buttons
    keyboard = []
    if category_id != "all":
        keyboard.append([InlineKeyboardButton("📂 Back to Categories", callback_data="categories")])
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )