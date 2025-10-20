import os
import telebot
import requests
from flask import Flask
from threading import Thread
import time

app = Flask(__name__)

# Your bot token - will be set as environment variable
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8338081238:AAHeUKy9XL7kgeUUvXdQExCMp9nQtqUhrFQ')
bot = telebot.TeleBot(BOT_TOKEN)

# Use HTTPS since Render allows it!
API_BASE_URL = "https://menuqrcode.onrender.com/api"

@app.route('/')
def home():
    return "✅ YSG Bot is running on Render!"

@app.route('/health')
def health():
    return {"status": "healthy"}

# API helper function
def api_request(endpoint):
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"API Error: {e}")
        return None

# Start command - shows store info and categories
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        store = api_request("/stores/public/slug/ysg")
        if not store:
            bot.reply_to(message, "❌ Store not available")
            return

        # Get categories
        categories = api_request(f"/categories/store/{store['_id']}")
        
        # Create store info message
        store_info = f"🏪 *{store['name']}*\n"
        if store.get('description'):
            store_info += f"📝 {store['description']}\n"
        if store.get('address'):
            store_info += f"📍 {store['address']}\n"
        if store.get('phone'):
            store_info += f"📞 {store['phone']}\n"
        
        # Send store info first
        bot.send_message(message.chat.id, store_info, parse_mode="Markdown")
        
        # Create category buttons
        if categories:
            keyboard = []
            for category in categories:
                keyboard.append([telebot.types.KeyboardButton(f"📂 {category['name']}")])
            
            # Add "All Items" button
            keyboard.append([telebot.types.KeyboardButton("🍽️ All Items")])
            
            markup = telebot.types.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            bot.send_message(message.chat.id, "📋 *Select a category:*", parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "📭 No categories available")
            
    except Exception as e:
        print(f"Start error: {e}")
        bot.reply_to(message, "❌ Error loading store information")

# Handle category selection
@bot.message_handler(func=lambda message: message.text and message.text.startswith('📂 '))
def handle_category(message):
    try:
        category_name = message.text[2:]  # Remove emoji
        
        # Get store first to get store ID
        store = api_request("/stores/public/slug/ysg")
        if not store:
            bot.reply_to(message, "❌ Store not available")
            return
            
        # Get all products for this store
        products = api_request(f"/products/public-store/slug/ysg")
        if not products:
            bot.reply_to(message, f"📭 No items in {category_name}")
            return
            
        # Get categories to find the right one
        categories = api_request(f"/categories/store/{store['_id']}")
        category = next((cat for cat in categories if cat['name'] == category_name), None)
        
        if category:
            # Filter products for this category
            category_products = [p for p in products if p.get('category') and p['category']['_id'] == category['_id']]
            
            if category_products:
                message_text = f"📂 *{category_name}*\n\n"
                for product in category_products:
                    price = f" - {product['price']}" if product.get('price') else ''
                    available = '✅' if product.get('isAvailable', True) else '❌'
                    message_text += f"{available} *{product['title']}*{price}\n"
                    if product.get('description'):
                        message_text += f"   📝 {product['description']}\n"
                    message_text += "\n"
                
                bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
            else:
                bot.reply_to(message, f"📭 No items found in {category_name}")
        else:
            bot.reply_to(message, "❌ Category not found")
            
    except Exception as e:
        print(f"Category error: {e}")
        bot.reply_to(message, "❌ Error loading category")

# Handle "All Items" selection
@bot.message_handler(func=lambda message: message.text == '🍽️ All Items')
def handle_all_items(message):
    try:
        products = api_request("/products/public-store/slug/ysg")
        
        if not products:
            bot.reply_to(message, "📭 No items found in the menu")
            return
            
        # Group by category
        products_by_category = {}
        for product in products:
            category_name = product.get('category', {}).get('name', 'Uncategorized')
            if category_name not in products_by_category:
                products_by_category[category_name] = []
            products_by_category[category_name].append(product)
        
        message_text = "🍽️ *All Items*\n\n"
        
        for category_name, category_products in products_by_category.items():
            message_text += f"📂 *{category_name}*\n"
            for product in category_products:
                price = f" - {product['price']}" if product.get('price') else ''
                available = '✅' if product.get('isAvailable', True) else '❌'
                message_text += f"{available} *{product['title']}*{price}\n"
            message_text += "\n"
        
        bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
        
    except Exception as e:
        print(f"All items error: {e}")
        bot.reply_to(message, "❌ Error loading menu")

# Help command
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """🤖 *YSG Menu Bot Help*

*Commands:*
/start - Show store menu
/help - Show this help

*Features:*
• Browse menu by categories  
• See all items
• View prices and descriptions

Use the buttons to navigate!"""
    
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

# Start bot polling
def run_bot():
    print("🤖 Starting Telegram bot...")
    while True:
        try:
            bot.polling(none_stop=True, interval=3, timeout=20)
        except Exception as e:
            print(f"Bot polling error: {e}")
            time.sleep(10)  # Wait before restarting

# Start bot in background thread
print("🚀 Starting bot thread...")
bot_thread = Thread(target=run_bot)
bot_thread.daemon = True
bot_thread.start()

# Start Flask app
if __name__ == '__main__':
    print("🌐 Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=False)