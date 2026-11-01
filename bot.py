import os, threading, random, logging
from flask import Flask
import telebot
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL") or os.environ.get("DB_URI")
DB_CH_ENV = os.environ.get("DB_CHANNEL")

print(f"BOT_TOKEN: {bool(BOT_TOKEN)}, MONGO: {bool(MONGO_URL)}, DB_CH: {DB_CH_ENV}")

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# DB setup with try-except - jate crash na kore
try:
    client = MongoClient(MONGO_URL)
    db = client["vjbot"]
    settings_col = db["settings"]
    files_col = db["files"]
    batches_col = db["batches"]
    print("✅ Mongo Connected")
except Exception as e:
    print(f"❌ Mongo Error: {e}")
    settings_col = None

def get_set():
    try:
        if not settings_col:
            return {"protect": False, "autodelete": 0, "fsub": [], "caption": "🎬 {file_name}", "short_on": False, "verify_on": False, "db_channel": int(DB_CH_ENV or 0)}
        s = settings_col.find_one({"_id":"main"})
        if not s:
            s = {"_id":"main", "protect": False, "autodelete": 0, "fsub": [], "caption": "🎬 {file_name}\n\nJoin @YourChannel", "short_on": False, "verify_on": False, "db_channel": int(DB_CH_ENV or 0)}
            settings_col.insert_one(s)
        return s
    except:
        return {"protect": False, "autodelete": 0, "fsub": [], "caption": "🎬 {file_name}", "short_on": False, "verify_on": False, "db_channel": int(DB_CH_ENV or 0)}

def update(k,v):
    try:
        settings_col.update_one({"_id":"main"}, {"$set":{k:v}}, upsert=True)
    except: pass

def get_db():
    s = get_set()
    return s.get("db_channel") or int(DB_CH_ENV or 0)

pending = {}
batch_mode = {}

@app.route('/')
def home():
    return "✅ Bot Live - Full Panel"

@bot.message_handler(commands=['start'])
def start(m):
    args = m.text.split()
    s = get_set()
    db_ch = get_db()
    # File get
    if len(args) > 1:
        fid = args[1]
        if fid.startswith("batch_"):
            try:
                data = batches_col.find_one({"batch_id":fid})
                if not data: return bot.send_message(m.chat.id, "❌ Batch not found")
                for i, mid in enumerate(data.get("mids", [])):
                    cap = data.get("captions", [])[i] if i < len(data.get("captions", [])) else ""
                    try:
                        bot.copy_message(m.chat.id, db_ch, mid, caption=cap if cap else None, protect_content=s.get("protect", False))
                    except: pass
            except Exception as e:
                bot.send_message(m.chat.id, f"Error: {e}")
            return
        else:
            try:
                data = files_col.find_one({"file_id":fid})
                if not data: return bot.send_message(m.chat.id, f"👋 Hi {m.from_user.first_name}\nFile not found")
                cap = data.get("caption","")
                bot.copy_message(m.chat.id, db_ch, data["msg_id"], caption=cap if cap else None, protect_content=s.get("protect", False))
            except Exception as e:
                bot.send_message(m.chat.id, f"Error: {e}")
            return
    bot.send_message(m.chat.id, f"👋 Hi {m.from_user.first_name}\n\n📂 File pathao - alada lekha dite parbe\n📦 /batch - multifile\n⚙️ /panel - sob setting")

@bot.message_handler(commands=['panel','settings'])
def panel(m):
    s = get_set()
    txt = f"""🛠️ **ALL SETTINGS - BOT ER VITORE**

🔒 Copy: {'❌ OFF' if s.get('protect') else '✅ ON (Sobai copy korte parbe)'}
📝 Caption: {s.get('caption','')[:80]}
⏳ AutoDel: {s.get('autodelete')}s
📢 FSub: {s.get('fsub')}
💰 Monet: {s.get('short_on')}
🎫 Verify: {s.get('verify_on')}
📡 Stream: OFF
📦 Multifile: ON
DB: {get_db()}
"""
    mk = telebot.types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        telebot.types.InlineKeyboardButton(f"Copy {'ON' if s.get('protect') else 'OFF'}", callback_data="prot"),
        telebot.types.InlineKeyboardButton(f"AutoDel {s.get('autodelete')}", callback_data="auto"),
        telebot.types.InlineKeyboardButton("📝 Set Caption", callback_data="setcap"),
        telebot.types.InlineKeyboardButton("📢 Add FSub", callback_data="addfsub"),
        telebot.types.InlineKeyboardButton("🗑️ Clear FSub", callback_data="clear"),
        telebot.types.InlineKeyboardButton("💰 Monet", callback_data="mon"),
        telebot.types.InlineKeyboardButton("Status", callback_data="status")
    )
    bot.send_message(m.chat.id, txt, reply_markup=mk, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    s = get_set()
    if c.data == "prot":
        update("protect", not s.get("protect", False))
        bot.answer_callback_query(c.id, "Copy toggled")
    elif c.data == "auto":
        nxt = 0 if s.get("autodelete") != 0 else 300
        update("autodelete", nxt)
        bot.answer_callback_query(c.id, f"Auto {nxt}")
    elif c.data == "clear":
        update("fsub", [])
        bot.answer_callback_query(c.id, "FSub cleared")
    elif c.data == "mon":
        update("short_on", not s.get("short_on", False))
        bot.answer_callback_query(c.id, "Monet toggled")
    elif c.data == "setcap":
        pending[c.from_user.id] = {"type":"caption"}
        bot.send_message(c.message.chat.id, "✏️ Notun caption likho:\n{file_name} use koro file name er jonno\nJemon: 🎬 {file_name} Join @channel")
        return
    elif c.data == "addfsub":
        pending[c.from_user.id] = {"type":"fsub"}
        bot.send_message(c.message.chat.id, "📢 FSub dao: @channel")
        return
    elif c.data == "status":
        cnt = 0
        try: cnt = files_col.count_documents({})
        except: pass
        bot.answer_callback_query(c.id, f"Files: {cnt}")
    try: panel(c.message)
    except: pass

@bot.message_handler(func=lambda m: m.from_user.id in pending and pending[m.from_user.id].get("type")=="caption")
def set_cap(m):
    update("caption", m.text)
    pending.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, f"✅ Caption set:\n{m.text}")

@bot.message_handler(func=lambda m: m.from_user.id in pending and pending[m.from_user.id].get("type")=="fsub")
def set_fsub(m):
    chans = [x for x in m.text.split() if x.startswith("@")]
    s = get_set()
    cur = s.get("fsub", [])
    cur.extend(chans)
    update("fsub", list(set(cur)))
    pending.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, f"✅ FSub added: {chans}")

@bot.message_handler(commands=['batch'])
def batch_start(m):
    batch_mode[m.from_user.id] = []
    bot.send_message(m.chat.id, "📦 Multifile ON\nFile pathao, lekha chaibo\nDone: /batch_done")

@bot.message_handler(commands=['batch_done'])
def batch_done(m):
    data = batch_mode.get(m.from_user.id, [])
    if not data: return bot.send_message(m.chat.id, "❌ Kono file nei")
    mids = [x[0] for x in data]
    caps = [x[1] for x in data]
    bid = f"batch_{random.randint(10000,999999)}"
    try:
        batches_col.update_one({"batch_id":bid}, {"$set":{"mids":mids,"captions":caps}}, upsert=True)
    except: pass
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
        update("db_channel", m.forward_from_chat.id)
        return bot.send_message(m.chat.id, f"✅ DB Set: {m.forward_from_chat.id}")
    db_ch = get_db()
    if not db_ch:
        return bot.send_message(m.chat.id, "❌ DB set koro - channel er ekta post forward koro")
    if m.from_user.id in batch_mode:
        if m.caption:
            try:
                f = bot.forward_message(db_ch, m.chat.id, m.message_id)
                batch_mode[m.from_user.id].append((f.message_id, m.caption))
                bot.send_message(m.chat.id, f"✅ Added {len(batch_mode[m.from_user.id])}")
            except: pass
        else:
            pending[m.from_user.id] = {"type":"file","msg_id":m.message_id,"is_batch":True}
            bot.send_message(m.chat.id, "✏️ Ei file er jonno ki likhbo? Lekha pathao\n/skip for no caption")
        return
    if m.caption:
        try:
            f = bot.forward_message(db_ch, m.chat.id, m.message_id)
            files_col.update_one({"file_id":f"file_{f.message_id}"}, {"$set":{"msg_id":f.message_id,"caption":m.caption}}, upsert=True)
            link = f"https://t.me/{bot.get_me().username}?start=file_{f.message_id}"
            bot.send_message(m.chat.id, f"✅ Saved\n📝 {m.caption}\n🔗 {link}")
        except Exception as e:
            bot.send_message(m.chat.id, f"Error {e}")
    else:
        pending[m.from_user.id] = {"type":"file","msg_id":m.message_id,"is_batch":False}
        bot.send_message(m.chat.id, "✏️ Ki likhbo? Movie name pathao\n/skip for no caption")

@bot.message_handler(func=lambda m: m.from_user.id in pending and pending[m.from_user.id].get("type")=="file")
def save_file_cap(m):
    cap = "" if m.text.startswith("/skip") else m.text
    data = pending.pop(m.from_user.id, None)
    if not data: return
    db_ch = get_db()
    try:
        f = bot.forward_message(db_ch, m.chat.id, data["msg_id"])
        if data["is_batch"]:
            batch_mode[m.from_user.id].append((f.message_id, cap))
            bot.send_message(m.chat.id, f"✅ Added - {cap[:30] if cap else 'No cap'}\nAro file ba /batch_done")
        else:
            files_col.update_one({"file_id":f"file_{f.message_id}"}, {"$set":{"msg_id":f.message_id,"caption":cap}}, upsert=True)
            link = f"https://t.me/{bot.get_me().username}?start=file_{f.message_id}"
            bot.send_message(m.chat.id, f"✅ Saved\n📝 {cap}\n🔗 {link}\n✅ Copy ON")
    except Exception as e:
        bot.send_message(m.chat.id, f"Error {e}")

def run_bot():
    try:
        bot.delete_webhook(drop_pending_updates=True)
        print("Webhook deleted")
    except Exception as e:
        print(f"Webhook err {e}")
    print("Bot polling start - Full Panel")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
        except Exception as e:
            print(f"Polling err {e}")
            import time
            time.sleep(5)

threading.Thread(target=run_bot, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
