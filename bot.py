import telebot, threading, time
from flask import Flask
import config
from database import get_settings, update_settings, save_file, get_file

bot = telebot.TeleBot(config.BOT_TOKEN, threaded=False)
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is Live - Final Version"

def get_db():
    s = get_settings()
    db = s.get("db_channel") or config.DB_CHANNEL
    return db

@bot.message_handler(commands=['start'])
def start(m):
    args = m.text.split()
    if len(args) > 1:
        data = get_file(args[1])
        if not data:
            bot.send_message(m.chat.id, "❌ File not found")
            return
        s = get_settings()
        try:
            bot.copy_message(m.chat.id, get_db(), data['msg_id'], protect_content=s.get("protect", False))
        except Exception as e:
            bot.send_message(m.chat.id, f"Error: {e}")
    else:
        bot.send_message(m.chat.id, f"Hi {m.from_user.first_name}\nBot Live ✅\nDB: {get_db()}\nSend /panel")

@bot.message_handler(content_types=['document','video','audio','photo'])
def files(m):
    if m.forward_from_chat:
        update_settings("db_channel", m.forward_from_chat.id)
        bot.send_message(m.chat.id, f"✅ DB Set: {m.forward_from_chat.id}\nEbar file pathao")
        return
    db = get_db()
    if not db or db==0:
        bot.send_message(m.chat.id, "❌ DB set koro:\nDB Channel er 1ta post ekhane forward koro")
        return
    try:
        fwd = bot.forward_message(db, m.chat.id, m.message_id)
        fid = f"file_{fwd.message_id}"
        save_file(fid, fwd.message_id)
        uname = bot.get_me().username
        link = f"https://t.me/{uname}?start={fid}"
        bot.send_message(m.chat.id, f"✅ Saved!\n🔗 {link}\nCopy ON")
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ Error: {e}\nBot ke DB Channel e admin koro")

@bot.message_handler(commands=['panel','settings','id'])
def panel(m):
    s = get_settings()
    txt = f"⚙️ Panel\nID: {m.from_user.id}\nDB: {get_db()}\nProtect: {s.get('protect')}\nCopy: {'OFF' if s.get('protect') else 'ON'}"
    mk = telebot.types.InlineKeyboardMarkup()
    mk.add(telebot.types.InlineKeyboardButton(f"Protect {s.get('protect')} (Copy toggle)", callback_data="prot"))
    mk.add(telebot.types.InlineKeyboardButton("Clear FSub", callback_data="clear"))
    bot.send_message(m.chat.id, txt, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    s = get_settings()
    if c.data=="prot":
        update_settings("protect", not s.get("protect", False))
        bot.answer_callback_query(c.id, "Changed! OFF = Copy ON")
    if c.data=="clear":
        update_settings("fsub", [])
        bot.answer_callback_query(c.id, "FSub cleared")
    s = get_settings()
    txt = f"⚙️ Panel\nID: {c.from_user.id}\nDB: {get_db()}\nProtect: {s.get('protect')}\nCopy: {'OFF' if s.get('protect') else 'ON'}"
    try:
        bot.edit_message_text(txt, c.message.chat.id, c.message.message_id, reply_markup=c.message.reply_markup)
    except:
        pass

@bot.message_handler(commands=['fsub'])
def fsub(m):
    try:
        ch = m.text.split()[1]
        s = get_settings()
        lst = s.get("fsub", [])
        if ch in lst: lst.remove(ch)
        else: lst.append(ch)
        update_settings("fsub", lst)
        bot.send_message(m.chat.id, f"FSub: {lst}")
    except:
        bot.send_message(m.chat.id, "Use: /fsub @channel")

def run():
    while True:
        try:
            print("Bot Running Final")
            bot.infinity_polling()
        except:
            time.sleep(5)
threading.Thread(target=run, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=10000)
