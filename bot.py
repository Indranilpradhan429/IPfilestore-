import telebot, threading, time, os, random
from flask import Flask
import config
from database import *

bot = telebot.TeleBot(config.BOT_TOKEN, threaded=False)
app = Flask(__name__)
batch_mode = {}
pending = {}

@app.route('/')
def home():
    return "✅ PRO Bot Live - Fixed"

def get_db():
    s = get_settings()
    db_id = s.get("db_channel") or config.DB_CHANNEL
    return db_id

@bot.message_handler(commands=['start'])
def start(m):
    add_user(m.from_user.id)
    args = m.text.split()
    s = get_settings()
    if len(args) > 1:
        fid = args[1]
        if fid.startswith("batch_"):
            data = get_batch(fid)
            if not data:
                bot.send_message(m.chat.id, "❌ Batch not found")
                return
            caps = data.get("captions", [])
            for i, mid in enumerate(data.get("mids", [])):
                cap = caps[i] if i < len(caps) else ""
                try:
                    bot.copy_message(m.chat.id, get_db(), mid, caption=cap if cap else None, protect_content=s.get("protect", False))
                except:
                    pass
            return
        else:
            data = get_file(fid)
            if not data:
                bot.send_message(m.chat.id, s.get("start_msg", "Hi").format(name=m.from_user.first_name))
                return
            try:
                cap = data.get("caption", "") or s.get("caption", "")
                bot.copy_message(m.chat.id, get_db(), data["msg_id"], caption=cap if cap else None, protect_content=s.get("protect", False))
            except Exception as e:
                bot.send_message(m.chat.id, f"Error: {e}")
            return
    bot.send_message(m.chat.id, s.get("start_msg", "Hi").format(name=m.from_user.first_name) + "\n\n📂 File pathao\n📦 /batch multifile\n⚙️ /panel")

@bot.message_handler(commands=['batch'])
def batch_start(m):
    batch_mode[m.from_user.id] = []
    bot.send_message(m.chat.id, "📦 Multifile ON\nFile pathao, lekha chaibo\nDone hole /batch_done")

@bot.message_handler(commands=['batch_done'])
def batch_done(m):
    data = batch_mode.get(m.from_user.id, [])
    if not data:
        bot.send_message(m.chat.id, "❌ Kono file nei")
        return
    mids = []
    caps = []
    for f_mid, cap in data:
        mids.append(f_mid)
        caps.append(cap)
    bid = f"batch_{random.randint(10000,999999)}"
    save_batch(bid, mids, caps)
    link = f"https://t.me/{bot.get_me().username}?start={bid}"
    bot.send_message(m.chat.id, f"✅ Saved {len(mids)} files\n🔗 {link}")
    batch_mode[m.from_user.id] = []

@bot.message_handler(commands=['batch_cancel'])
def batch_cancel(m):
    batch_mode.pop(m.from_user.id, None)
    pending.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "❌ Cancelled")

@bot.message_handler(content_types=['document','video','audio','photo'])
def handle_file(m):
    if m.forward_from_chat:
        update_settings("db_channel", m.forward_from_chat.id)
        bot.send_message(m.chat.id, f"✅ DB Set: {m.forward_from_chat.id}")
        return
    db = get_db()
    if not db:
        bot.send_message(m.chat.id, "❌ DB set koro")
        return
    if m.from_user.id in batch_mode:
        if m.caption:
            try:
                f = bot.forward_message(db, m.chat.id, m.message_id)
                batch_mode[m.from_user.id].append((f.message_id, m.caption))
                bot.send_message(m.chat.id, f"✅ Added {len(batch_mode[m.from_user.id])}")
            except:
                pass
        else:
            pending[m.from_user.id] = {"msg_id": m.message_id, "is_batch": True}
            bot.send_message(m.chat.id, "✏️ Ei file er jonno ki likhbo? Lekha pathao\n/skip for no caption")
        return
    if m.caption:
        try:
            f = bot.forward_message(db, m.chat.id, m.message_id)
            save_file(f"file_{f.message_id}", f.message_id, m.caption)
            link = f"https://t.me/{bot.get_me().username}?start=file_{f.message_id}"
            bot.send_message(m.chat.id, f"✅ Saved\n📝 {m.caption}\n🔗 {link}")
        except Exception as e:
            bot.send_message(m.chat.id, f"Error {e}")
    else:
        pending[m.from_user.id] = {"msg_id": m.message_id, "is_batch": False}
        bot.send_message(m.chat.id, "✏️ Ki likhbo? Movie name pathao\n/skip for no caption")

@bot.message_handler(func=lambda m: m.from_user.id in pending)
def save_caption(m):
    if not m.text:
        return
    cap = "" if m.text.startswith("/skip") else m.text
    data = pending.pop(m.from_user.id)
    db = get_db()
    try:
        f = bot.forward_message(db, m.chat.id, data["msg_id"])
        if data["is_batch"]:
            batch_mode[m.from_user.id].append((f.message_id, cap))
            bot.send_message(m.chat.id, f"✅ Added - {cap[:30] if cap else 'No cap'}\nAro pathao ba /batch_done")
        else:
            fid = f"file_{f.message_id}"
            save_file(fid, f.message_id, cap)
            link = f"https://t.me/{bot.get_me().username}?start={fid}"
            bot.send_message(m.chat.id, f"✅ Saved\n📝 {cap}\n🔗 {link}\n✅ Copy ON")
    except Exception as e:
        bot.send_message(m.chat.id, f"Error {e}")

@bot.message_handler(commands=['panel'])
def panel(m):
    s = get_settings()
    txt = f"Panel\nCopy: {'ON' if not s.get('protect') else 'OFF'}\nDB: {get_db()}"
    mk = telebot.types.InlineKeyboardMarkup()
    mk.add(telebot.types.InlineKeyboardButton(f"Copy Toggle", callback_data="prot"))
    mk.add(telebot.types.InlineKeyboardButton("Clear FSub", callback_data="clear"))
    bot.send_message(m.chat.id, txt, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    s = get_settings()
    if c.data == "prot":
        update_settings("protect", not s.get("protect", False))
    if c.data == "clear":
        update_settings("fsub", [])
    bot.answer_callback_query(c.id, "Done")

def run_bot():
    try:
        bot.delete_webhook()
    except:
        pass
    while True:
        try:
            print("Bot Running")
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(e)
            time.sleep(5)

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
