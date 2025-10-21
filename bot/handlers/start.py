from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from bot.menu_api import MenuAPI

def start(update: Update, context: CallbackContext):
    """Send welcome message and show main menu"""
    store_info = MenuAPI.get_store_info()
    store_name = store_info.get('name', 'YSG Store') if store_info else 'YSG Store'
    
    keyboard = [
        [InlineKeyboardButton("📂 Categories", callback_data="categories")],
        [InlineKeyboardButton("🍽️ All Products", callback_data="category_all")],
        [InlineKeyboardButton("🏪 Store Info", callback_data="store_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        update.message.reply_text(
            f"Welcome to {store_name}! 🍕\nBrowse our menu:",
            reply_markup=reply_markup
        )
    else:
        update.callback_query.edit_message_text(
            f"Welcome to {store_name}! 🍕\nBrowse our menu:",
            reply_markup=reply_markup
        )

def store_info(update: Update, context: CallbackContext):
    """Show store information"""
    query = update.callback_query
    query.answer()
    
    store_info = MenuAPI.get_store_info()
    
    if not store_info:
        query.edit_message_text("Store information not available.")
        return
    
    # Format store info message
    message = f"🏪 *{store_info.get('name', 'YSG Store')}*\n\n"
    
    if store_info.get('description'):
        message += f"📝 {store_info['description']}\n\n"
    
    if store_info.get('phone'):
        message += f"📞 {store_info['phone']}\n"
    
    if store_info.get('address'):
        message += f"📍 {store_info['address']}\n"
    
    # Social media links
    social_links = []
    if store_info.get('facebookUrl'):
        social_links.append(f"[Facebook]({store_info['facebookUrl']})")
    if store_info.get('telegramUrl'):
        social_links.append(f"[Telegram]({store_info['telegramUrl']})")
    if store_info.get('tiktokUrl'):
        social_links.append(f"[TikTok]({store_info['tiktokUrl']})")
    
    if social_links:
        message += f"\n🔗 {' | '.join(social_links)}"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )