import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

from bot.menu_api import MenuAPI
from bot.handlers.start import start
from bot.handlers.categories import show_categories, handle_category_select
from bot.handlers.products import show_products, handle_product_detail

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
        
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("menu", start))
        application.add_handler(CallbackQueryHandler(show_categories, pattern="^categories$"))
        application.add_handler(CallbackQueryHandler(handle_category_select, pattern="^category_"))
        application.add_handler(CallbackQueryHandler(show_products, pattern="^products_"))
        application.add_handler(CallbackQueryHandler(start, pattern="^main_menu$"))
        application.add_handler(CallbackQueryHandler(show_categories, pattern="^back_categories$"))
        
        # Start the Bot
        logger.info("Bot is starting...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == '__main__':
    main()