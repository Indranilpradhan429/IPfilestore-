import telebot, config, database, time, random, string, requests, threading
from flask import Flask
from telebot import types

bot = telebot.TeleBot(config.BOT_TOKEN, threaded=False)
app = Flask(__name__)
batch_mode = {}

def is_admin(uid):
    return uid == config.ADMIN_ID

def short_gen():
    return ''.join(random.choices(string.ascii_letters+string.digits, k=8))

def shorten(url):
    s = database.get_settings()
    api = s.get("short_api") or config.SHORT_API
    domain = s.get("short_url") or config.SHORT_URL
    if not api: return url
    try:
        r = requests.get(f"https://{domain}/api?api={api}&url={url}", timeout=10).json()
        return r.get("shortenedUrl") or r.get("shortened") or url
    except:
        return url

def build_caption(f_doc, sett):
    orig = f_doc.get("orig_caption","")
    fname = f_doc.get("name","File")
    bname = bot.get_me().username
    custom = sett.get("caption","📁 {filename}").format(filename=fname, botusername=bname)
    mode = sett.get("caption_mode","both")
    if mode == "both" and orig:
        return f"{orig}\n\n{custom}"
    elif mode == "custom":
        return custom
    elif mode == "orig":
        return orig
    return custom if custom else orig

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    args = m.text.split()
    sett = database.get_settings()
    # Fsub check
    for ch in sett.get("fsub",[]):
        try:
            st = bot.get_chat_member(ch, uid).status
            if st not in ['member','administrator','creator']:
                btn = types.InlineKeyboardMarkup()
                btn.add(types.InlineKeyboardButton("Join Channel", url=f"https://t.me/{ch.replace('@','')}"))
                btn.add(types.InlineKeyboardButton("✅ Joined, Try Again", url=f"https://t.me/{bot.get_me().username}?start={args[1] if len(args)>1 else ''}"))
                bot.send_message(uid, "❌ Join our channel first!", reply_markup=btn)
                return
        except: pass

    if len(args) > 1:
        file_id = args[1]
        f = database.files.find_one({"_id": file_id})
        if not f:
            # Batch
            b = database.files.find_one({"_id": file_id, "type":"batch"})
            if b:
                for fid in b.get("files",[]):
                    fd = database.files.find_one({"_id": fid})
                    if fd:
                        cap = build_caption(fd, sett)
                        bot.copy_message(uid, config.DB_CHANNEL, fd["msg_id"], caption=cap, protect_content=sett.get("protect",False))
                return
            bot.send_message(uid, "❌ File not found!")
            return
        cap = build_caption(f, sett)
        # Buttons
        markup = None
        if sett.get("custom_buttons"):
            markup = types.InlineKeyboardMarkup()
            for b in sett.get("custom_buttons"):
                if "|" in b:
                    t,u = b.split("|",1)
                    markup.add(types.InlineKeyboardButton(t.strip(), url=u.strip()))
        sent = bot.copy_message(uid, config.DB_CHANNEL, f["msg_id"], caption=cap, reply
