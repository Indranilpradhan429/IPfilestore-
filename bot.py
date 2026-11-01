import telebot, threading, os, random
from flask import Flask
from database import get_set, update, files, batches

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

pending = {}
batch_mode = {}

@app.route('/')
def home():
    return "✅ Bot Live - All Settings in Bot"

def get_db():
    s = get_set()
    return s.get("db_channel") or int(os.environ.get("DB_CHANNEL", 0))

# START + FILE GET
@bot.message_handler(commands=['start'])
def start(m):
    args = m.text.split()
    s = get_set()
    if len(args) > 1:
        fid = args[1]
        if fid.startswith("batch_"):
            data = batches.find_one({"batch_id":fid})
            if not data: return bot.send_message(m.chat.id, "❌ Not found")
            for i, mid in enumerate(data.get("mids", [])):
                cap = data.get("captions", [])[i] if i < len(data.get("captions", [])) else ""
                final_cap = cap or s.get("caption","").replace("{file_name}", "")
                try:
                    bot.copy_message(m.chat.id, get_db(), mid, caption=final_cap if final_cap else None, protect_content=s.get("protect", False))
                except: pass
            return
        else:
            data = files.find_one({"file_id":fid})
            if not data: return bot.send_message(m.chat.id, "👋 Hi")
            cap = data.get("caption","")
            final_cap = cap or s.get("caption","").replace("{file_name}", "")
            try:
                bot.copy_message(m.chat.id, get_db(), data["msg_id"], caption=final_cap if final_cap else None, protect_content=s.get("protect", False))
            except Exception as e:
                bot.send_message(m.chat.id, f"Error {e}")
            return
    bot.send_message(m.chat.id, f"👋 Hi {m.from_user.first_name}\n\n📂 File pathao\n📦 /batch - multifile\n⚙️ /panel - sob setting")

# PANEL - SOB SETTING BOT ER VITORE
@bot.message_handler(commands=['panel','settings','id'])
def panel(m):
    s = get_set()
    txt = f"""🛠️ **ALL SETTINGS IN BOT**

🔒 **Copy Setting:**
{'❌ OFF (Keu copy korte parbe na)' if s.get('protect') else '✅ ON (Sobai copy korte parbe)'}

📝 **Caption:**
{s.get('caption','')[:100]}

⏳ **AutoDelete:** {s.get('autodelete',0)}s ({'OFF - Permanent' if s.get('autodelete',0)==0 else 'ON'})

📢 **FSub:** {len(s.get('fsub',[]))} channels
{s.get('fsub',[])}

💰 **Monetization:** {s.get('short_on')}
🎫 **Verify:** {s.get('verify_on')}

📦 **Multifile:** ON
🔗 **Permanent Link:** ON
📡 **Stream:** OFF (Tomar kotha moto)

DB: {get_db()}
Files: {files.count_documents({})}
"""
    mk = telebot.types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        telebot.types.InlineKeyboardButton(f"Copy {'OFF' if s.get('protect') else 'ON'} ✅", callback_data="prot"),
        telebot.types.InlineKeyboardButton(f"AutoDel {s.get('autodelete')}s", callback_data="auto"),
        telebot.types.InlineKeyboardButton("📝 Set Caption", callback_data="setcap"),
        telebot.types.InlineKeyboardButton("📢 Add FSub", callback_data="addfsub"),
        telebot.types.InlineKeyboardButton("🗑️ Clear FSub", callback_data="clearfsub"),
        telebot.types.InlineKeyboardButton("💰 Monet ON/OFF", callback_data="mon"),
        telebot.types.InlineKeyboardButton("🎫 Verify ON/OFF", callback_data="ver"),
        telebot.types.InlineKeyboardButton("📊 Status", callback_data="status")
    )
    bot.send_message(m.chat.id, txt, reply_markup=mk, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    s = get_set()
    if c.data == "prot":
        update("protect", not s.get("protect", False))
        bot.answer_callback_query(c.id, f"Copy {'ON' if s.get('protect')==False else 'OFF'} holo")
    elif c.data == "auto":
        nxt = 0 if s.get("autodelete") != 0 else 300
        update("autodelete", nxt)
        bot.answer_callback_query(c.id, f"AutoDelete {nxt}s")
    elif c.data == "clearfsub":
        update("fsub", [])
        bot.answer_callback_query(c.id, "FSub cleared")
    elif c.data == "mon":
        update("short_on", not s.get("short_on", False))
        bot.answer_callback_query(c.id, "Monetization toggled")
    elif c.data == "ver":
        update("verify_on", not s.get("verify_on", False))
        bot.answer_callback_query(c.id, "Verify toggled")
    elif c.data == "status":
        bot.answer_callback_query(c.id, f"Files: {files.count_documents({})}")
    elif c.data == "setcap":
        pending[c.from_user.id] = {"type":"caption"}
        bot.send_message(c.message.chat.id, "✏️ **Notun caption likho:**\n\n`{file_name}` dile file er name asbe\n\nJemon:\n🎬 {file_name}\nJoin @YourChannel\n\nLekha pathao")
        return
    elif c.data == "addfsub":
        pending[c.from_user.id] = {"type":"fsub"}
        bot.send_message(c.message.chat.id, "📢 **FSub channel er username dao:**\nJemon: @YourChannel\nBa @channel1 @channel2")
        return
    try:
        panel(c.message)
    except: pass

@bot.message_handler(func=lambda m: m.from_user.id in pending and pending[m.from_user.id].get("type")=="caption")
def set_caption(m):
    update("caption", m.text)
    pending.pop(m.from_user.id)
    bot.send_message(m.chat.id, f"✅ Caption set:\n{m.text}\n\nEbar file pathao, ei caption auto asbe")

@bot.message_handler(func=lambda m: m.from_user.id in pending and pending[m.from_user.id].get("type")=="fsub")
def set_fsub(m):
    chans = [x for x in m.text.split() if x.startswith("@")]
    s = get_set()
    cur = s.get("fsub", [])
    cur.extend(chans)
    update("fsub", list(set(cur)))
    pending.pop(m.from_user.id)
    bot.send_message(m.chat.id, f"✅ FSub added: {chans}")

# BATCH
@bot.message_handler(commands=['batch'])
def batch_start(m):
    batch_mode[m.from_user.id] = []
    bot.send_message(m.chat.id, "📦 Multifile ON\nFile pathao, prottekta te alada lekha chaibo\nDone: /batch_done")

@bot.message_handler(commands=['batch_done'])
def batch_done(m):
    data = batch_mode.get(m.from_user.id, [])
    if not data:
        bot.send_message(m.chat.id, "❌ Kono file nei")
        return
    mids = [x[0] for x in data]
    caps = [x[1] for x in data]
    bid = f"batch_{random.randint(10000,999999)}"
    batches.update_one({"batch_id":bid}, {"$set":{"mids":mids,"captions":caps}}, upsert=True)
    link = f"https://t.me/{bot.get_me().username}?start={bid}"
    bot.send_message(m.chat.id, f"✅ Multifile Saved {len(mids)} files\n🔗 {link}\nProttekta te alada lekha")
    batch_mode[m.from_user.id] = []

@bot.message_handler(commands=['batch_cancel'])
def batch_cancel(m):
    batch_mode.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "❌ Cancelled")

# FILE HANDLE + ALADA LEKHA CHAIBE
@bot.message_handler(content_types=['document','video','audio','photo'])
def handle_file(m):
    if m.forward_from_chat:
        update("db_channel", m.forward_from_chat.id)
        bot.send_message(m.chat.id, f"✅ DB Set: {m.forward_from_chat.id}\nEbar file pathao")
        return
    db = get_db()
    if not db:
        bot.send_message(m.chat.id, "❌ DB set koro - channel er ekta post forward koro")
        return
    if m.from_user.id in batch_mode:
        if m.caption:
            f = bot.forward_message(db, m.chat.id, m.message_id)
            batch_mode[m.from_user.id].append((f.message_id, m.caption))
            bot.send_message(m.chat.id, f"✅ Added {len(batch_mode[m.from_user.id])} - {m.caption[:20]}")
        else:
            pending[m.from_user.id] = {"type":"file","msg_id":m.message_id,"is_batch":True}
            bot.send_message(m.chat.id, "✏️ Ei file er jonno ki likhbo? Movie name pathao\n/skip dile caption chara")
        return
    if m.caption:
        f = bot.forward_message(db, m.chat.id, m.message_id)
        files.update_one({"file_id":f"file_{f.message_id}"}, {"$set":{"msg_id":f.message_id,"caption":m.caption}}, upsert=True)
        link = f"https://t.me/{bot.get_me().username}?start=file_{f.message_id}"
        bot.send_message(m.chat.id, f"✅ Saved\n📝 {m.caption}\n🔗 {link}")
    else:
        pending[m.from_user.id] = {"type":"file","msg_id":m.message_id,"is_batch":False}
        bot.send_message(m.chat.id, "✏️ **Ki likhbo ei file er niche?**\nMovie name / description likho\nJemon: Dadagiri S02E12\n/skip likhle khali save hobe")

@bot.message_handler(func=lambda m: m.from_user.id in pending and pending[m.from_user.id].get("type")=="file")
def save_file_cap(m):
    cap = "" if m.text.startswith("/skip") else m.text
    data = pending.pop(m.from_user.id)
    db = get_db()
    f = bot.forward_message(db, m.chat.id, data["msg_id"])
    if data["is_batch"]:
        batch_mode[m.from_user.id].append((f.message_id, cap))
        bot.send_message(m.chat.id, f"✅ Added - {cap[:30] if cap else 'No cap'}\nAro file ba /batch_done")
    else:
        files.update_one({"file_id":f"file_{f.message_id}"}, {"$set":{"msg_id":f.message_id,"caption":cap}}, upsert=True)
        link = f"https://t.me/{bot.get_me().username}?start=file_{f.message_id}"
        bot.send_message(m.chat.id, f"✅ Saved\n📝 {cap}\n🔗 {link}\n✅ Copy ON")

def run():
    try: bot.delete_webhook()
    except: pass
    while True:
        try:
            print("Bot Running - All Settings in Bot")
            bot.infinity_polling()
        except: pass

threading.Thread(target=run, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=10000)
