import os, time, requests, threading
import telebot
from telebot import types
from flask import Flask
import config
from database import get_settings, update_settings, save_file, get_file

bot = telebot.TeleBot(config.BOT_TOKEN, threaded=False)
app = Flask(__name__)

def get_db_channel():
    s = get_settings()
    # Age settings e thakle seta use korbe, na hole config theke
    return s.get("db_channel") or config.DB_CHANNEL

@app.route('/')
def home():
    return "✅ Bot Live - Auto DB Mode"

@bot.message_handler(commands=['start'])
def start_cmd(m):
    args = m.text.split()
    if len(args) > 1:
        file_id = args[1]
        s = get_settings()
        for ch in s.get("fsub", []):
            try:
                st = bot.get_chat_member(ch, m.from_user.id).status
                if st in ['left', 'kicked']:
                    bot.send_message(m.chat.id, f"⚠️ Join: {ch}")
                    return
            except:
                pass
        data = get_file(file_id)
        if not data:
            bot.send_message(m.chat.id, "❌ File not found!")
            return
        try:
            db_ch = get_db_channel()
            sent = bot.copy_message(m.chat.id, db_ch, data['msg_id'], protect_content=s.get("protect", False))
        except Exception as e:
            bot.send_message(m.chat.id, f"❌ DB Error: {e}\n/setdb command use korun")
    else:
        bot.send_message(m.chat.id, f"👋 Hello {m.from_user.first_name}!\nBot Running ✅\nDB: {get_db_channel()}")

# Eita holo main fix - channel theke forward korle auto set hobe
@bot.message_handler(content_types=['document', 'video', 'audio', 'photo'])
def save(m):
    # Jodi channel theke forward hoye ase (forward_from_chat thakle)
    if m.forward_from_chat:
        update_settings("db_channel", m.forward_from_chat.id)
        bot.send_message(m.chat.id, f"✅ DB Channel Auto Set! ID: {m.forward_from_chat.id}\nEbar theke ekhane save hobe.")
        return

    try:
        db_ch = get_db_channel()
        if not db_ch or db_ch == 0:
            bot.send_message(m.chat.id, "❌ Age DB Channel set korun:\n1. DB Channel er ekta post forward korun ekhane\n2. Bot auto set kore nebe")
            return
            
        sent = bot.forward_message(db_ch, m.chat.id, m.message_id)
        file_id = f"file_{sent.message_id}"
        save_file(file_id, sent.message_id)
        bot_username = bot.get_me().username
        link = f"https://t.me/{bot_username}?start={file_id}"
        bot.send_message(m.chat.id, f"✅ Saved!\n\n🔗 Link: {link}\n📂 DB: {db_ch}")
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ Error: {e}\n\nFix:\n1. Bot ke DB Channel e admin korun\n2. DB Channel er ekta post ekhane forward korun, bot ID dhore nebe")

@bot.message_handler(commands=['setdb', 'panel', 'settings', 'id'])
def panel(m):
    s = get_settings()
    txt = f"⚙️ **Panel**\n\nYour ID: {m.from_user.id}\nDB Channel: {get_db_channel()}\nProtect: {s.get('protect')}\nFSub: {s.get('fsub')}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"Protect: {s.get('protect')}", callback_data="toggle_protect"))
    markup.add(types.InlineKeyboardButton("Autodelete OFF = Copy ON", callback_data="auto_0"))
    bot.send_message(m.chat.id, txt, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    s = get_settings()
    if c.data == "toggle_protect":
        update_settings("protect", not s.get("protect", False))
        bot.answer_callback_query(c.id, f"Protect: {not s.get('protect', False)}")
    elif c.data == "auto_0":
        update_settings("autodelete", 0)
        bot.answer_callback_query(c.id, "Copy ON - Autodelete OFF")

def run_bot():
    while True:
        try:
            print("Bot Running - Auto DB Mode")
            bot.infinity_polling()
        except Exception as e:
            print(e)
            time.sleep(5)

threading.Thread(target=run_bot, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
