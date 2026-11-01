import os, threading, logging
from flask import Flask
import telebot

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.environ.get("BOT_TOKEN")

print("=== DEBUG ===")
print(f"BOT_TOKEN exists: {bool(BOT_TOKEN)}")
if BOT_TOKEN:
    print(f"Token start: {BOT_TOKEN[:15]}...")
print(f"MONGO_URL exists: {bool(os.environ.get('MONGO_URL') or os.environ.get('DB_URI'))}")
print(f"DB_CHANNEL: {os.environ.get('DB_CHANNEL')}")
print("=============")

if not BOT_TOKEN:
    print("❌ BOT_TOKEN missing! Render Env e BOT_TOKEN set koro")
    # Keep Flask alive to see log
    app = Flask(__name__)
    @app.route('/')
    def home():
        return "❌ BOT_TOKEN Missing - Set in Render Env"
    app.run(host="0.0.0.0", port=10000)
else:
    bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
    app = Flask(__name__)

    @app.route('/')
    def home():
        return "✅ Bot Running - Reply Test"

    @bot.message_handler(commands=['start','panel','test','settings'])
    def handle_start(m):
        print(f"📩 Got /start from {m.from_user.id}")
        try:
            bot.send_message(m.chat.id, f"✅ BOT REPLY KORCHE!\n\nID: {m.from_user.id}\nName: {m.from_user.first_name}\n\nEbar full setting wala code bosabo.\n/panel likhle panel asbe.")
            print("✅ Reply sent")
        except Exception as e:
            print(f"❌ Send failed: {e}")

    @bot.message_handler(func=lambda m: True)
    def handle_any(m):
        print(f"📩 Got message: {m.text} from {m.from_user.id}")
        bot.send_message(m.chat.id, f"Got: {m.text}\nBot alive ✅")

    def run_bot():
        print("Deleting webhook...")
        try:
            bot.delete_webhook(drop_pending_updates=True)
            print("Webhook deleted")
        except Exception as e:
            print(f"Webhook error: {e}")
        
        print("Starting polling...")
        while True:
            try:
                bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
            except Exception as e:
                print(f"Polling error: {e}")
                import time
                time.sleep(5)

    threading.Thread(target=run_bot, daemon=True).start()
    print("Flask starting...")

    if __name__ == "__main__":
        app.run(host="0.0.0.0", port=10000)
