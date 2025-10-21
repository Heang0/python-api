import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from dotenv import load_dotenv

from bot.menu_api import MenuAPI
from bot.handlers.start import start, store_info
from bot.handlers.categories import show_categories, handle_category_select
from bot.handlers.products import show_products

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_BASE_URL = os.getenv('API_BASE_URL')
STORE_SLUG = os.getenv('STORE_SLUG', 'ysg')

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Start the bot"""
    try:
        # Initialize MenuAPI with config
        MenuAPI.API_BASE_URL = API_BASE_URL
        MenuAPI.STORE_SLUG = STORE_SLUG
        
        # Use Updater instead of Application (for v13.x)
        updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # Add handlers
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("menu", start))
        dispatcher.add_handler(CallbackQueryHandler(show_categories, pattern="^categories$"))
        dispatcher.add_handler(CallbackQueryHandler(handle_category_select, pattern="^category_"))
        dispatcher.add_handler(CallbackQueryHandler(show_products, pattern="^products_"))
        dispatcher.add_handler(CallbackQueryHandler(store_info, pattern="^store_info$"))
        dispatcher.add_handler(CallbackQueryHandler(start, pattern="^main_menu$"))
        
        # Start the Bot
        logger.info("Bot is starting...")
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == '__main__':
    main()