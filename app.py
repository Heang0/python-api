import asyncio
import threading
import logging
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health_check():
    return {"status": "healthy", "service": "YSG Telegram Bot"}

def run_bot():
    """Run the bot in its own event loop"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        from bot.telegram_bot import main
        logging.info("Starting Telegram bot...")
        loop.run_until_complete(main())
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")

# Start bot when app starts
if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
else:
    # For Gunicorn
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()