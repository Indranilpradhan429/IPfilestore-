import telebot, config, database, time, random, string, requests, threading
from flask import Flask
from telebot import types

bot = telebot.TeleBot(config.BOT_TOKEN, threaded=False)
app = Flask(__name__)
batch_mode = {}

def is_admin(uid):
    return uid == config.ADMIN_ID

def short_gen():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def shorten(url):
    s = database.get_settings()
    api = s.get("short_api") or config.SHORT_API
    domain = s.get("short_url") or config.SHORT_URL
    if not api:
        return url
    try:
        r = requests.get(f"https://{domain}/api?api={api}&url={url}", timeout=10).json()
        return r.get("shortenedUrl") or url
    except:
        return url

def build_caption(f_doc, sett):
    orig = f_doc.get("orig_caption", "")
    fname = f_doc.get("name", "File")
    custom = sett.get("caption", "📁 {filename}").format(filename=fname)
    mode = sett.get("caption_mode", "both")
    if mode == "both" and orig:
        return f"{orig}\n\n{custom}"
    if mode == "orig":
        return orig
    return custom

@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = m.from_user.id
    args = m.text.split()
    sett = database.get_settings()
    if len(args) > 1:
        fid = args[1]
        f = database.files.find_one({"_id": fid})
        if not f:
            bot.send_message(uid, "❌ File not found!")
            return
        cap = build_caption(f, sett)
        bot.copy_message(uid, config.DB_CHANNEL, f["msg_id"], caption=cap, protect_content=sett.get("protect", False))
    else:
        txt = sett.get("start_msg", "Hello {name}!").format(name=m.from_user.first_name)
        bot.send_message(uid, txt)

@bot.message_handler(commands=['settings'])
def settings_cmd(m):
    if not is_admin(m.from_user.id):
        return
    s = database.get_settings()
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("🔗 FSub", callback_data="fsub"),
        types.InlineKeyboardButton("🛡️ Protect", callback_data="protect"),
        types.InlineKeyboardButton("⏱️ AutoDel", callback_data="autodel"),
        types.InlineKeyboardButton("💰 Shortener", callback_data="short"),
        types.InlineKeyboardButton("🔘 Buttons", callback_data="buttons")
    )
    bot.send_message(m.chat.id, f"Settings\nShort: {s.get('short_url')}\nProtect: {s.get('protect')}\nAutoDel: {s.get('autodelete')}m", reply_markup=mk)

@bot.callback_query_handler(func=lambda x: True)
def cb(call):
    if not is_admin(call.from_user.id):
        return
    s = database.get_settings()
    if call.data == "short":
        bot.send_message(call.message.chat.id, "Send: API,DOMAIN\nEx: abc123,shrinkme.io")
        bot.register_next_step_handler(call.message, save_short)
    elif call.data == "protect":
        database.update_settings("protect", not s.get("protect", False))
        bot.answer_callback_query(call.id, "Toggled")
    elif call.data == "autodel":
        bot.send_message(call.message.chat.id, "Send minutes (0=off)")
        bot.register_next_step_handler(call.message, save_autodel)
    elif call.data == "fsub":
        bot.send_message(call.message.chat.id, f"Current: {s.get('fsub')}\nSend @channels comma separated")
        bot.register_next_step_handler(call.message, save_fsub)
    elif call.data == "buttons":
        bot.send_message(call.message.chat.id, "Send: Text | https://t.me/xxx")
        bot.register_next_step_handler(call.message, save_buttons)

def save_short(m):
    try:
        api, dom = m.text.split(",", 1)
        database.update_settings("short_api", api.strip())
        database.update_settings("short_url", dom.strip())
        bot.send_message(m.chat.id, f"✅ Saved: {dom.strip()}")
    except:
        bot.send_message(m.chat.id, "❌ Wrong format")

def save_fsub(m):
    chs = [x.strip() for x in m.text.split(",")]
    database.update_settings("fsub", chs)
    bot.send_message(m.chat.id, "✅ FSub saved")

def save_autodel(m):
    try:
        v = int(m.text)
        database.update_settings("autodelete", v)
        bot.send_message(m.chat.id, f"✅ AutoDel {v}m")
    except:
        bot.send_message(m.chat.id, "Number only")

def save_buttons(m):
    btns = m.text.split("\n")
    database.update_settings("custom_buttons", btns)
    bot.send_message(m.chat.id, "✅ Buttons saved")

@bot.message_handler(content_types=['document','video','audio','photo'])
def save_file(m):
    if not is_admin(m.from_user.id):
        return
    fwd = bot.forward_message(config.DB_CHANNEL, m.chat.id, m.message_id)
    file_id = short_gen()
    name = "file"
    if m.document:
        name = m.document.file_name
    elif m.video:
        name = m.video.file_name or "video.mp4"
    elif m.photo:
        name = "photo.jpg"
    orig = m.caption or ""
    database.files.insert_one({"_id": file_id, "msg_id": fwd.message_id, "name": name, "orig_caption": orig})
    share = f"https://t.me/{bot.get_me().username}?start={file_id}"
    short_link = shorten(share)
    bot.send_message(m.chat.id, f"✅ Saved\n\nFileName:\n`{name}`\n\nLink: {short_link}", parse_mode="Markdown")

@app.route('/')
def home():
    return "Bot Running"

def run_bot():
    bot.infinity_polling()

threading.Thread(target=run_bot).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
