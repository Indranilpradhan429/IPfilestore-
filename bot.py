import os, time, requests, threading
import telebot
from telebot import types
from flask import Flask
import config
from database import get_settings, update_settings, save_file, get_file

bot = telebot.TeleBot(config.BOT_TOKEN, threaded=False)
app = Flask(__name__)
ADMIN = config.ADMIN_ID

def is_admin(uid):
    return uid == ADMIN

def short_link(url):
    s = get_settings()
    if not s.get("shortlink") or not s.get("short_api"):
        return url
    try:
        api = f"https://{s['short_url']}/api?api={s['short_api']}&url={url}"
        r = requests.get(api, timeout=5).json()
        return r.get("shortenedUrl", url)
    except:
        return url

@app.route('/')
def home():
    return "✅ Bot is Live - Full Feature"

@bot.message_handler(commands=['start'])
def start_cmd(m):
    args = m.text.split()
    if len(args) > 1:
        file_id = args[1]
        # FSub Check
        s = get_settings()
        for ch in s.get("fsub", []):
            try:
                st = bot.get_chat_member(ch, m.from_user.id).status
                if st in ['left', 'kicked']:
                    bot.send_message(m.chat.id, f"⚠️ Join korun: {ch} tarpor abar /start din")
                    return
            except:
                pass
        
        data = get_file(file_id)
        if not data:
            bot.send_message(m.chat.id, "❌ File not found!")
            return
        
        try:
            # Copy from DB Channel
            sent = bot.copy_message(m.chat.id, config.DB_CHANNEL, data['msg_id'], protect_content=s.get("protect", False))
            # Autodelete
            if s.get("autodelete", 0) > 0:
                time.sleep(s["autodelete"])
                try:
                    bot.delete_message(m.chat.id, sent.message_id)
                except:
                    pass
        except Exception as e:
            bot.send_message(m.chat.id, f"Error: {e}\nMake sure bot is admin in DB Channel")
    else:
        bot.send_message(m.chat.id, f"👋 Hello {m.from_user.first_name}!\nBot is Running ✅")

# File Save - Only Admin
@bot.message_handler(content_types=['document', 'video', 'audio', 'photo'])
def save(m):
    if not is_admin(m.from_user.id):
        return
    try:
        sent = bot.forward_message(config.DB_CHANNEL, m.chat.id, m.message_id)
        file_id = f"file_{sent.message_id}"
        save_file(file_id, sent.message_id)
        bot_username = bot.get_me().username
        link = f"https://t.me/{bot_username}?start={file_id}"
        s_link = short_link(link)
        bot.send_message(m.chat.id, f"✅ Saved!\n\n🔗 Link: {link}\n🔗 Short: {s_link}")
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ Error: {e}\nDB_CHANNEL e bot admin korun")

# Admin Settings
@bot.message_handler(commands=['settings', 'panel'])
def settings_cmd(m):
    if not is_admin(m.from_user.id):
        return
    s = get_settings()
    txt = f"⚙️ **Settings Panel**\n\nProtect: {s.get('protect')}\nAutodelete: {s.get('autodelete')}s\nShortlink: {s.get('shortlink')}\nFSub: {s.get('fsub')}\nCaption: {s.get('caption')}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Protect ON/OFF", callback_data="toggle_protect"))
    markup.add(types.InlineKeyboardButton("Shortlink ON/OFF", callback_data="toggle_short"))
    bot.send_message(m.chat.id, txt, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    if not is_admin(c.from_user.id):
        return
    s = get_settings()
    if c.data == "toggle_protect":
        update_settings("protect", not s.get("protect", False))
        bot.answer_callback_query(c.id, f"Protect: {not s.get('protect', False)}")
    elif c.data == "toggle_short":
        update_settings("shortlink", not s.get("shortlink", False))
        bot.answer_callback_query(c.id, f"Shortlink: {not s.get('shortlink', False)}")

@bot.message_handler(commands=['fsub'])
def fsub_cmd(m):
    if not is_admin(m.from_user.id):
        return
    try:
        ch = m.text.split()[1]
        s = get_settings()
        fsubs = s.get("fsub", [])
        if ch in fsubs:
            fsubs.remove(ch)
        else:
            fsubs.append(ch)
        update_settings("fsub", fsubs)
        bot.send_message(m.chat.id, f"FSub Updated: {fsubs}")
    except:
        bot.send_message(m.chat.id, "Usage: /fsub @channelusername")

@bot.message_handler(commands=['stats'])
def stats_cmd(m):
    if not is_admin(m.from_user.id):
        return
    bot.send_message(m.chat.id, "Bot is Live ✅\nAll features working!")

def run_bot():
    while True:
        try:
            print("Bot Running - Full Feature")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(5)

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
