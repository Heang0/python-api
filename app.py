from flask import Flask
import threading
import os
import logging

app = Flask(__name__)

@app.route('/')
def health_check():
    return {
        "status": "healthy", 
        "service": "YSG Telegram Bot",
        "message": "Bot is running via polling"
    }

@app.route('/health')
def health():
    return {"status": "ok"}

# Import and start the bot in a separate thread
def start_bot():
    try:
        from bot.telegram_bot import main
        logging.info("Starting Telegram bot...")
        main()
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")

# Start the bot when the app starts
if __name__ == "__main__":
    # Start bot in a separate thread
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    logging.info("Bot thread started")
    
    # Start Flask app
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
else:
    # For Gunicorn
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    logging.info("Bot thread started (Gunicorn)")