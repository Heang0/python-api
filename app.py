import os
import logging
import requests
import asyncio
import time
from flask import Flask, request, jsonify
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from threading import Thread
import threading

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration - UPDATE THESE WITH YOUR ACTUAL URLs
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8338081238:AAHeUKy9XL7kgeUUvXdQExCMp9nQtqUhrFQ')
# Update this to match your actual backend URL
API_BASE_URL = "https://menuqrcode.onrender.com/api"  # CHANGE THIS TO YOUR BACKEND URL!
RENDER_URL = "https://python-api-912v.onrender.com"

# Add API headers if your backend requires authentication
API_HEADERS = {
    'Content-Type': 'application/json',
    # 'Authorization': 'Bearer your-api-token'  # Uncomment if needed
}

# Global application instance
application = None
bot_setup_done = False

# Cache
cache = {
    'store': None,
    'categories': None,
    'products': None,
    'last_fetch': 0
}
CACHE_DURATION = 300000  # 5 minutes

# Flask routes
@app.route('/')
def home():
    bot_status = "✅ Done" if bot_setup_done else "❌ Failed"
    store_status = "✅" if cache['store'] else "❌"
    categories_status = "✅" if cache['categories'] else "❌" 
    products_status = "✅" if cache['products'] else "❌"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>YSG Telegram Bot</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; text-align: center; }}
            .status {{ color: #22c55e; font-size: 24px; margin: 20px 0; }}
            .error {{ color: #ef4444; }}
            .debug {{ margin: 20px; padding: 15px; background: #f3f4f6; border-radius: 5px; text-align: left; }}
        </style>
    </head>
    <body>
        <h1>🍽️ YSG Store Telegram Bot</h1>
        <div class="status">✅ Bot is running with Webhook!</div>
        <p>Go to Telegram and send <code>/start</code> to your bot.</p>
        
        <div class="debug">
            <h3>Debug Info:</h3>
            <p><strong>Bot Setup:</strong> {bot_status}</p>
            <p><strong>API Base URL:</strong> {API_BASE_URL}</p>
            <p><strong>Cache Status:</strong> Store: {store_status}, Categories: {categories_status}, Products: {products_status}</p>
            <a href="/debug/api">Test API Connection</a> | 
            <a href="/health">Health Check</a>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'platform': 'python',
        'webhook': True,
        'bot_setup': bot_setup_done,
        'cache': {
            'store_loaded': bool(cache['store']),
            'categories_loaded': bool(cache['categories']),
            'products_loaded': bool(cache['products'])
        }
    })

@app.route('/debug/api')
def debug_api():
    """Test API connectivity"""
    store, categories, products = get_cached_data()
    
    debug_info = {
        'api_base_url': API_BASE_URL,
        'store_endpoint_working': bool(store),
        'categories_endpoint_working': bool(categories),
        'products_endpoint_working': bool(products),
        'categories_count': len(categories) if categories else 0,
        'products_count': len(products) if products else 0,
        'cache_fresh': time.time() * 1000 - cache['last_fetch'] < CACHE_DURATION
    }
    
    return jsonify(debug_info)

# Webhook route - Telegram sends updates here
@app.route('/webhook', methods=['POST'])
def webhook():
    global application
    try:
        if application is None:
            logger.error("Application not initialized")
            return 'Bot not initialized', 500
            
        # Get the update from Telegram
        update_data = request.get_json()
        if not update_data:
            logger.error("No JSON data in webhook request")
            return 'No data', 400
            
        logger.info(f"Received webhook update")
        
        # Create Update object
        update = Update.de_json(update_data, application.bot)
        
        # Use the application's update queue
        application.update_queue.put_nowait(update)
        
        return 'OK'
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'OK', 200

# API functions
def api_request(endpoint):
    try:
        full_url = f"{API_BASE_URL}{endpoint}"
        logger.info(f"Making API request to: {full_url}")
        
        response = requests.get(
            full_url, 
            headers=API_HEADERS,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        
        logger.info(f"API Response from {endpoint}: Status {response.status_code}")
        return data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API Request Error ({endpoint}): {e}")
        return None
    except ValueError as e:
        logger.error(f"API JSON Parse Error ({endpoint}): {e}")
        return None

def get_cached_data():
    current_time = time.time() * 1000
    
    if (cache['store'] is not None and cache['products'] is not None and 
        (current_time - cache['last_fetch']) < CACHE_DURATION):
        logger.info("Using cached data")
        return cache['store'], cache['categories'], cache['products']
    
    logger.info("Fetching fresh data from API")
    
    # Try endpoints - adjust these based on your actual API
    store = api_request('/stores/public/slug/ysg')
    categories = api_request('/categories/store/slug/ysg')
    products = api_request('/products/public-store/slug/ysg')
    
    logger.info(f"Store data: {store is not None}")
    logger.info(f"Categories count: {len(categories) if categories else 0}")
    logger.info(f"Products count: {len(products) if products else 0}")
    
    if store or products:
        cache['store'] = store
        cache['categories'] = categories or []
        cache['products'] = products or []
        cache['last_fetch'] = current_time
    
    return store, categories, products

# Keyboard layouts
def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📋 Main Menu"), KeyboardButton("📂 Categories")],
        [KeyboardButton("🍽️ All Items"), KeyboardButton("🔄 Refresh")],
        [KeyboardButton("🏪 Store Info"), KeyboardButton("❓ Help")]
    ], resize_keyboard=True, persistent=True)

def categories_keyboard(categories):
    keyboard = []
    if categories:
        for category in categories[:8]:
            category_name = category.get('name') or category.get('title', 'Unknown')
            keyboard.append([KeyboardButton(f"📂 {category_name}")])
    
    keyboard.append([KeyboardButton("📋 Main Menu"), KeyboardButton("🍽️ All Items")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Bot command handlers
async def start_command(update: Update, context: CallbackContext):
    welcome_text = """👋 *Welcome to YSG Store!* 🏪

I'm your digital menu assistant. Here's what I can do:

• 📋 *Browse our menu* by categories
• 🍽️ *View all items* at once  
• 🖼️ *See product images* and prices
• 🔄 *Refresh* for latest menu

Use the buttons below or type /menu to begin!"""

    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

async def menu_command(update: Update, context: CallbackContext):
    menu_text = """🎛️ *YSG Store Main Menu*

Choose an option below:

• *📂 Categories* - Browse by category
• *🍽️ All Items* - View everything
• *🏪 Store Info* - Contact & location
• *🔄 Refresh* - Get latest menu
• *❓ Help* - Get assistance"""

    await update.message.reply_text(
        menu_text,
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

async def categories_command(update: Update, context: CallbackContext):
    await update.message.reply_text("🔄 Loading categories...")
    await show_categories(update.message.chat_id)

async def all_command(update: Update, context: CallbackContext):
    await update.message.reply_text("🔄 Loading all items...")
    await handle_all_items(update.message.chat_id)

async def help_command(update: Update, context: CallbackContext):
    help_text = """🤖 *YSG Store Bot Help*

*Available Commands:*
/start - Start the bot
/menu - Show main menu
/categories - Browse categories
/all - View all items
/help - This help message

*Tips:*
• Use /refresh if menu seems outdated
• Tap categories to browse specific items
• Contact store for orders/questions"""

    await update.message.reply_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

# Button handlers
async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text
    chat_id = update.message.chat_id
    
    if text == "📋 Main Menu":
        await menu_command(update, context)
    elif text == "📂 Categories":
        await show_categories(chat_id)
    elif text == "🍽️ All Items":
        await handle_all_items(chat_id)
    elif text == "🔄 Refresh":
        await handle_refresh(chat_id)
    elif text == "🏪 Store Info":
        await handle_store_info(chat_id)
    elif text == "❓ Help":
        await help_command(update, context)
    elif text.startswith("📂 "):
        category_name = text[3:]
        await handle_category(chat_id, category_name)

async def show_categories(chat_id):
    try:
        store, categories, products = get_cached_data()
        
        if not categories:
            await application.bot.send_message(
                chat_id, 
                "📭 No categories found. Showing all items instead..."
            )
            await handle_all_items(chat_id)
            return
        
        await application.bot.send_message(
            chat_id,
            f"📋 *Categories*\n\n{len(categories)} categories available. Tap one to browse:",
            parse_mode='Markdown',
            reply_markup=categories_keyboard(categories)
        )
        
    except Exception as e:
        logger.error(f"Show categories error: {e}")
        await application.bot.send_message(
            chat_id,
            "❌ Error loading categories. Please try /menu",
            reply_markup=main_menu_keyboard()
        )

async def handle_category(chat_id, category_name):
    try:
        await application.bot.send_message(chat_id, f"🔄 Loading {category_name}...")
        
        store, categories, products = get_cached_data()
        
        if not products:
            await application.bot.send_message(
                chat_id,
                "❌ Menu temporarily unavailable. Please try /refresh",
                reply_markup=main_menu_keyboard()
            )
            return
        
        category_products = products  # Show all products for now
        
        if category_products:
            await application.bot.send_message(
                chat_id,
                f"📂 *{category_name}*\n_{len(category_products)} items found_",
                parse_mode='Markdown'
            )
            
            for i, product in enumerate(category_products[:6]):
                await send_product(chat_id, product)
                
        else:
            await application.bot.send_message(
                chat_id,
                f"📭 No items found in *{category_name}*.\n\nTry /all to see all items.",
                parse_mode='Markdown'
            )
            
        await application.bot.send_message(
            chat_id,
            "👇 Continue browsing:",
            reply_markup=main_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Category error: {e}")
        await application.bot.send_message(
            chat_id,
            "❌ Error loading category. Please try /menu",
            reply_markup=main_menu_keyboard()
        )

async def handle_all_items(chat_id):
    try:
        store, categories, products = get_cached_data()
        
        if products:
            await application.bot.send_message(
                chat_id,
                f"🍽️ *All Menu Items*\n_{len(products)} items total_",
                parse_mode='Markdown'
            )
            
            for i, product in enumerate(products[:6]):
                await send_product(chat_id, product)
                
            if len(products) > 6:
                await application.bot.send_message(
                    chat_id,
                    f"📋 Showing 6 out of {len(products)} items. Visit our store for full menu!",
                    parse_mode='Markdown'
                )
        else:
            await application.bot.send_message(
                chat_id, 
                "📭 No items found in the menu. Please try /refresh",
                reply_markup=main_menu_keyboard()
            )
            
        await application.bot.send_message(
            chat_id,
            "👇 Continue browsing:",
            reply_markup=main_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"All items error: {e}")
        await application.bot.send_message(
            chat_id,
            "❌ Error loading menu. Please try /refresh",
            reply_markup=main_menu_keyboard()
        )

async def send_product(chat_id, product):
    try:
        title = product.get('title') or product.get('name', 'Unnamed Product')
        price = product.get('price')
        description = product.get('description') or product.get('desc', '')
        
        price_text = f" - ${price}" if price else ''
        caption = f"🍽️ *{title}*{price_text}\n{description}"
        
        image_url = product.get('image') or product.get('imageUrl')
        
        if image_url:
            try:
                await application.bot.send_photo(
                    chat_id,
                    image_url,
                    caption=caption,
                    parse_mode='Markdown'
                )
                return
            except Exception as e:
                logger.warning(f"Could not send photo for {title}: {e}")
        
        await application.bot.send_message(
            chat_id,
            caption,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Send product error for {product.get('title', 'unknown')}: {e}")

async def handle_refresh(chat_id):
    cache['store'] = None
    cache['categories'] = None
    cache['products'] = None
    cache['last_fetch'] = 0
    
    await application.bot.send_message(chat_id, "🔄 Refreshing menu data...")
    
    store, categories, products = get_cached_data()
    
    if products:
        await application.bot.send_message(
            chat_id,
            f"✅ Menu refreshed! Found {len(products)} items.",
            reply_markup=main_menu_keyboard()
        )
    else:
        await application.bot.send_message(
            chat_id,
            "⚠️ Could not fetch menu data. Please try again later.",
            reply_markup=main_menu_keyboard()
        )

async def handle_store_info(chat_id):
    try:
        store, categories, products = get_cached_data()
        
        if store:
            store_name = store.get('name', 'YSG Store')
            store_info = f"🏪 *{store_name}*\n\n"
            
            if store.get('description'):
                store_info += f"📝 {store['description']}\n\n"
            if store.get('address'):
                store_info += f"📍 *Address:* {store['address']}\n"
            if store.get('phone'):
                store_info += f"📞 *Phone:* {store['phone']}\n"
            
            await application.bot.send_message(
                chat_id,
                store_info,
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        else:
            await application.bot.send_message(
                chat_id,
                "🏪 *YSG Store*\n\n📍 Visit us for delicious food!",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
    except Exception as e:
        logger.error(f"Store info error: {e}")
        await application.bot.send_message(
            chat_id,
            "❌ Error loading store info.",
            reply_markup=main_menu_keyboard()
        )

# Setup bot
async def setup_bot():
    global application, bot_setup_done
    
    try:
        logger.info("Starting bot setup...")
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("menu", menu_command))
        application.add_handler(CommandHandler("categories", categories_command))
        application.add_handler(CommandHandler("all", all_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Set bot commands
        await application.bot.set_my_commands([
            ("start", "Start the bot"),
            ("menu", "Show main menu"),
            ("categories", "Browse categories"),
            ("all", "View all items"),
            ("help", "Get help")
        ])
        
        # Set webhook
        webhook_url = f"{RENDER_URL}/webhook"
        await application.bot.set_webhook(webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")
        
        # Initialize the application
        await application.initialize()
        await application.start()
        
        bot_setup_done = True
        logger.info("Telegram bot started successfully with webhook!")
        
    except Exception as e:
        logger.error(f"Bot setup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        bot_setup_done = False

# Run bot setup in background
def start_bot():
    logger.info("Starting bot thread...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_bot())
    logger.info("Bot setup completed in thread")

# Start bot when app starts
logger.info("Starting Flask app...")
bot_thread = Thread(target=start_bot, daemon=True)
bot_thread.start()

# For Render deployment
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)