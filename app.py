import os
import logging
import requests
from flask import Flask, request, jsonify
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8338081238:AAHeUKy9XL7kgeUUvXdQExCMp9nQtqUhrFQ')
API_BASE_URL = "https://menuqrcode.onrender.com/api"
RENDER_URL = "https://python-api-912v.onrender.com"  # Your Render URL

# Global application instance
application = None

# Cache
cache = {
    'store': None,
    'categories': None,
    'products': None,
    'last_fetch': 0
}
CACHE_DURATION = 60000  # 1 minute

# Flask routes
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YSG Telegram Bot</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
            .status { color: #22c55e; font-size: 24px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>🍽️ YSG Store Telegram Bot</h1>
        <div class="status">✅ Bot is running with Webhook!</div>
        <p>Go to Telegram and send <code>/start</code> to your bot.</p>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'platform': 'python',
        'webhook': True
    })

# Webhook route - Telegram sends updates here
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(), application.bot)
        application.update_queue.put(update)
        return 'OK'
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'OK', 200

# API functions
def api_request(endpoint):
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"API Error ({endpoint}): {e}")
        return None

def get_cached_data():
    import time
    current_time = time.time() * 1000  # Convert to milliseconds
    
    if (cache['store'] and cache['products'] and 
        (current_time - cache['last_fetch']) < CACHE_DURATION):
        logger.info("Using cached data")
        return cache['store'], cache['categories'], cache['products']
    
    logger.info("Fetching fresh data from API")
    store = api_request('/stores/public/slug/ysg')
    categories = api_request('/categories/store/slug/ysg')
    products = api_request('/products/public-store/slug/ysg')
    
    if store and products:
        cache['store'] = store
        cache['categories'] = categories
        cache['products'] = products
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
        for category in categories:
            keyboard.append([KeyboardButton(f"📂 {category['name']}")])
    
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
• *❓ Help* - Get assistance

You can also type commands like:
/categories - Browse categories
/all - View all items
/help - Get help"""

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

*How to Use:*
1. Send /start to begin
2. Use the menu buttons at the bottom
3. Browse categories or view all items
4. Products show with images and prices

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
        
        category_products = products
        if categories:
            category = next((cat for cat in categories if cat['name'] == category_name), None)
            if category:
                category_products = [p for p in products if p.get('category') and p['category']['_id'] == category['_id']]
        
        if category_products:
            await application.bot.send_message(
                chat_id,
                f"📂 *{category_name}*\n_{len(category_products)} items found_",
                parse_mode='Markdown'
            )
            
            for i, product in enumerate(category_products[:10]):  # Limit to 10 items
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
            
            for i, product in enumerate(products[:8]):  # Limit to 8 items
                await send_product(chat_id, product)
        else:
            await application.bot.send_message(chat_id, "📭 No items found in the menu.")
            
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
        price = f" - {product['price']} 💵" if product.get('price') else ''
        available = '❌ ' if product.get('isAvailable') is False else '✅ '
        caption = f"{available}*{product['title']}*{price}\n{product.get('description', '')}"
        
        image_url = product.get('image') or product.get('imageUrl')
        
        if image_url:
            try:
                await application.bot.send_photo(
                    chat_id,
                    image_url,
                    caption=caption,
                    parse_mode='Markdown'
                )
            except Exception as e:
                await application.bot.send_message(
                    chat_id,
                    caption,
                    parse_mode='Markdown'
                )
        else:
            await application.bot.send_message(
                chat_id,
                caption,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Send product error: {e}")

async def handle_refresh(chat_id):
    cache['store'] = None
    cache['categories'] = None
    cache['products'] = None
    cache['last_fetch'] = 0
    
    await application.bot.send_message(chat_id, "🔄 Refreshing menu data...")
    await application.bot.send_message(
        chat_id,
        "✅ Menu refreshed! Use the buttons below:",
        reply_markup=main_menu_keyboard()
    )

async def handle_store_info(chat_id):
    try:
        store, categories, products = get_cached_data()
        
        if store:
            store_info = f"🏪 *{store['name']}*\n\n"
            if store.get('description'):
                store_info += f"📝 {store['description']}\n\n"
            if store.get('address'):
                store_info += f"📍 *Address:* {store['address']}\n"
            if store.get('phone'):
                store_info += f"📞 *Phone:* {store['phone']}\n"
            
            # Social links
            social_links = []
            if store.get('facebookUrl'):
                social_links.append(f"• [Facebook]({store['facebookUrl']})")
            if store.get('telegramUrl'):
                social_links.append(f"• [Telegram]({store['telegramUrl']})")
            if store.get('websiteUrl'):
                social_links.append(f"• [Website]({store['websiteUrl']})")
            
            if social_links:
                store_info += '\n🔗 *Follow Us:*\n' + '\n'.join(social_links)

            await application.bot.send_message(
                chat_id,
                store_info,
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        else:
            await application.bot.send_message(
                chat_id,
                "❌ Store information not available.",
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
    global application
    
    # Create Application
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
        ("start", "🚀 Start the bot"),
        ("menu", "📋 Show main menu"),
        ("categories", "📂 Browse categories"),
        ("all", "🍽️ View all items"),
        ("help", "❓ Get help")
    ])
    
    # Set webhook
    webhook_url = f"{RENDER_URL}/webhook"
    await application.bot.set_webhook(webhook_url)
    logger.info(f"✅ Webhook set to: {webhook_url}")
    
    # Initialize application
    await application.initialize()
    await application.start()
    
    logger.info("✅ Telegram bot started successfully with webhook!")

# Initialize bot when app starts
@app.before_first_request
def initialize_bot():
    import asyncio
    try:
        # Run the async setup
        asyncio.run(setup_bot())
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")

# For Render deployment
if __name__ == '__main__':
    # Initialize bot
    import asyncio
    try:
        asyncio.run(setup_bot())
    except Exception as e:
        logger.error(f"Bot setup failed: {e}")
    
    # Start Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)