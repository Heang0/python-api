# This is a simple Flask app wrapper for the Telegram bot
# Render expects a web service, but Telegram bot uses polling
# This creates a simple health check endpoint

from flask import Flask
import threading
import os

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
    from bot.telegram_bot import main
    main()

if __name__ == "__main__":
    # Start bot in a separate thread
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    # Start Flask app (for Render's web service requirement)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)