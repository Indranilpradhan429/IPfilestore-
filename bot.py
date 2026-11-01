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
    return "✅ PRO Bot Live - All Features - Copy ON - Multifile"

def get_db():
    return get_settings().get("db_channel") or config.DB_CHANNEL

@bot.message_handler(commands=['start'])
def start(m):
    add_user(m.from_user.id)
    args = m.text.split()
    s = get_settings()
    if len(args)>1:
        fid = args[1]
        if fid.startswith("batch_"):
            data = get_batch(fid)
            if not data: return bot.send_message(m.chat.id, "❌ Batch not found")
            for i, mid in enumerate(data['mids']):
                cap = data['captions'][i] if i < len(data.get('captions',[])) else ""
                try:
                    bot.copy_message(m.chat.id, get_db(), mid, caption=cap if cap else None, protect_content=s.get("protect",False))
                except: pass
            return
        else:
            data = get_file(fid)
            if not data: return bot.send_message(m.chat.id, s.get("start_msg","Hi").format(name=m.from_user.first_name))
            try:
                cap = data.get("caption","") or s.get("caption","")
                bot.copy_message(m.chat.id, get_db(), data['msg_id'], caption=cap if cap else None, protect_content=s.get("protect",False))
            except Exception as e:
                bot.send_message(m.chat.id, f"Error: {e}")
            return
    bot.send_message(m.chat.id, s.get("start_msg","Hi").format(name=m.from_user.first_name) + "\n\n📂 File pathao - alada lekha dite parbe\n📦 /batch - akbare onek file\n⚙️ /panel")

@bot.message_handler(commands=['batch'])
def batch_start(m):
    batch_mode[m.from_user.id] = []
    bot.send_message(m.chat.id, "📦 Multifile Mode ON\nEbar file gulo pathao, prottekta file er jonno ami lekha chaibo\nSes hole /batch_done\nCancel /batch_cancel")

@bot.message_handler(commands=['batch_done'])
def batch_done(m):
    data = batch_mode.get(m.from_user.id, [])
    if not data: return bot.send_message(m.chat.id, "❌ Kono file nei")
    db = get_db()
    mids = []
    caps = []
    for f_mid, cap in data:
        mids.append(f_mid)
        caps.append(cap)
    bid = f"batch_{random.randint(10000,999999)}"
    save_batch(bid, mids, caps)
    link = f"https://t.me/{bot.get_me().username}?start={bid}"
    bot.send_message(m.chat.id, f"✅ Multifile Saved! {len(mids)} ta file\n🔗 {link}\nProttekta file er alada lekha save holo\n✅ Copy ON | Permanent Link")
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
        return bot.send_message(m.chat.id, f"✅ DB Set: {m.forward_from_chat.id}\nEbar file pathao")
    db = get_db()
    if not db: return bot.send_message(m.chat.id, "❌ DB set koro - channel er post forward koro")
    
    # Batch mode
    if m.from_user.id in batch_mode:
        if m.caption:
            try:
                f = bot.forward_message(db, m.chat.id, m.message_id)
                batch_mode[m.from_user.id].append((f.message_id, m.caption))
                bot.send_message(m.chat.id, f"✅ Added ({len(batch_mode[m.from_user.id])}) - {m.caption[:20]}")
            except: pass
        else:
            pending[m.from_user.id] = {"msg_id": m.message_id, "is_batch": True}
            bot.send_message(m.chat.id, f"✏️ File {len(batch_mode[m.from_user.id])+1} er jonno ki likhbo?\nLekha pathao, jemon: Dadagiri Part 1\n/skip dile lekha chara save hobe")
        return

    # Single file
    if m.caption:
        try:
            f = bot.forward_message(db, m.chat.id, m.message_id)
            save_file(f"file_{f.message_id}", f.message_id, m.caption)
            link = f"https://t.me/{bot.get_me().username}?start=file_{f.message_id}"
            bot.send_message(m.chat.id, f"✅ Saved!\n📝 {m.caption}\n🔗 {link}")
        except Exception as e:
            bot.send_message(m.chat.id, f"Error {e}")
    else:
        pending[m.from_user.id] = {"msg_id": m.message_id, "is_batch": False}
        bot.send_message(m.chat.id, "✏️ **Ei file er niche ki likhbo?**\nMovie name / description likho\n/skip dile khali save hobe")

@bot.message_handler(func=lambda m: m.from_user.id in pending)
def save_caption(m):
    if not m.text: return
    cap = "" if m.text.startswith("/skip") else m.text
    data = pending.pop(m.from_user.id)
    db = get_db()
    try:
        f = bot.forward_message(db, m.chat.id, data["msg_id"])
        if data["is_batch"]:
            batch_mode[m.from_user.id].append((f.message_id, cap))
            bot.send_message(m.chat.id, f"✅ Added - Lekha: {cap[:30] if cap else 'No caption'}\nAro file pathao ba /batch_done likho")
        else:
            fid = f"file_{f.message_id}"
            save_file(fid, f.message_id, cap)
            link = f"https://t.me/{bot.get_me().username}?start={fid}"
            bot.send_message(m.chat.id, f"✅ Saved!\n📝 {cap if cap else 'No caption'}\n🔗 {link}\n✅ Copy ON")
    except Exception as e:
        bot.send_message(m.chat.id, f"Error {e}")

@bot.message_handler(commands=['panel'])
def panel(m):
    s = get_settings()
    txt = f"🛠️ BOT MANAGEMENT\n\nCopy: {'ON' if not s.get('protect') else 'OFF'}\nMonetization: {s.get('short_on')}\nVerify: {s.get('verify_on')}\nFSub: {len(s.get('fsub',[]))}\nAutoDel: {s.get('autodelete')}s\nMultifile: ON\nPermanent: ON\nUsers: {files_col.count_documents({})}\nDB: {get_db()}"
    mk = telebot.types.InlineKeyboardMarkup(row_width=2)
    mk.add(telebot.types.InlineKeyboardButton(f"Copy {'OFF' if s.get('protect') else 'ON'}", callback_data="prot"),
           telebot.types.InlineKeyboardButton(f"Monet {s.get('short_on')}", callback_data="mon"),
           telebot.types.InlineKeyboardButton("Clear FSub", callback_data="clear"),
           telebot.types.InlineKeyboardButton("Status", callback_data="status"))
    bot.send_message(m.chat.id, txt, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    s = get_settings()
    if c.data=="prot": update_settings("protect", not s.get("protect",False))
    if c.data=="mon": update_settings("short_on", not s.get("short_on",False))
    if c.data=="clear": update_settings("fsub", [])
    bot.answer_callback_query(c.id, "Done")
    try: panel(c.message)
    except: pass

def run():
    try: bot.delete_webhook()
    except: pass
    while True:
        try:
            print("PRO Bot Running All Files")
            bot.infinity_polling(timeout=60)
        except: time.sleep(5)
threading.Thread(target=run, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=10000))
    )


async def admin_callback(update, context):
    query = update.callback_query
    user_id = query.from_user.id

    if not await admin_check(user_id):
        await query.answer("Not authorized.", show_alert=True)
        return

    data = query.data

    if data.startswith("toggle:"):
        key = data.split(":", 1)[1]
        old = await db.get_setting(key, "off")
        await db.set_setting(key, "off" if old == "on" else "on")
        await query.answer("Setting updated.")
        await admin_panel_refresh(query)

    elif data == "stats":
        from database import DB_PATH
        import aiosqlite

        async with aiosqlite.connect(DB_PATH) as database:
            users = (await (
                await database.execute("SELECT COUNT(*) FROM users")
            ).fetchone())[0]
            shares = (await (
                await database.execute("SELECT COUNT(*) FROM shares")
            ).fetchone())[0]
            files = (await (
                await database.execute("SELECT COUNT(*) FROM files")
            ).fetchone())[0]

        await query.answer()
        await query.message.reply_text(
            f"📊 Statistics\n\nUsers: {users}\n"
            f"Collections: {shares}\nFiles: {files}"
        )

    elif data == "channels":
        channels = await db.get_channels()
        text = "📢 Required channels:\n"
        text += "\n".join(
            f"{title}: {channel_id}"
            for channel_id, title, join in channels
        ) or "No channels configured."

        await query.answer()
        await query.message.reply_text(
            text + "\n\nUse /addchannel CHANNEL_ID TITLE"
        )


async def admin_panel_refresh(query):
    keys = [
        ("multiple_files", "Multiple files"),
        ("auto_delete", "Auto delete"),
        ("protect_content", "Protect content"),
        ("monetization", "Monetization"),
        ("shortener", "Link shortener"),
        ("token_verification", "Token verification"),
        ("force_subscribe", "Force subscription"),
        ("referral", "Referral system"),
        ("premium", "Premium plans"),
    ]

    buttons = []

    for key, title in keys:
        value = await db.get_setting(key, "off")
        status = "ON 🟢" if value == "on" else "OFF 🔴"
        buttons.append([
            InlineKeyboardButton(
                f"{title}: {status}",
                callback_data=f"toggle:{key}"
            )
        ])

    buttons.extend([
        [InlineKeyboardButton("📊 Statistics", callback_data="stats")],
        [InlineKeyboardButton("📢 Channels", callback_data="channels")]
    ])

    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def add_channel_command(update, context):
    if not await admin_check(update.effective_user.id):
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /addchannel CHANNEL_ID TITLE"
        )
        return

    try:
        channel_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid channel ID.")
        return

    title = " ".join(context.args[1:])

    await db.add_channel(channel_id, title)
    await update.message.reply_text("✅ Channel added.")


async def feature_setting(update, context):
    if not await admin_check(update.effective_user.id):
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /set KEY VALUE"
        )
        return

    key, value = context.args
    await db.set_setting(key, value)
    await update.message.reply_text("Setting saved.")


async def delete_channel_command(update, context):
    if not await admin_check(update.effective_user.id):
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /delchannel CHANNEL_ID"
        )
        return

    try:
        channel_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid channel ID.")
        return

    import aiosqlite
    async with aiosqlite.connect(db.DB_PATH) as database:
        await database.execute(
            "DELETE FROM channels WHERE channel_id=?",
            (channel_id,)
        )
        await database.commit()

    await update.message.reply_text("Channel removed.")


async def error_handler(update, context):
    logging.exception("Bot error", exc_info=context.error)


async def post_init(application):
    await db.init_db()
    await db.set_setting("multiple_files", "on")
    await db.set_setting("streaming", "off")


def main():
    global application

    if not TOKEN or OWNER == 0 or STORAGE == 0:
        raise RuntimeError(
            "Set BOT_TOKEN, OWNER_ID and STORAGE_CHANNEL_ID."
        )

    application = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("new", new))
    application.add_handler(CommandHandler("done", done))
    application.add_handler(CommandHandler("cancel", cancel))

    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("addchannel", add_channel_command))
    application.add_handler(CommandHandler("delchannel", delete_channel_command))
    application.add_handler(CommandHandler("set", feature_setting))

    application.add_handler(
        CallbackQueryHandler(check_sub_callback, pattern="^check_sub$")
    )
    application.add_handler(
        CallbackQueryHandler(admin_callback, pattern="^(toggle:|stats$|channels$)")
    )

    media_filter = (
        filters.Document.ALL | filters.PHOTO | filters.VIDEO |
        filters.AUDIO | filters.ANIMATION | filters.VOICE
    )

    application.add_handler(
        MessageHandler(media_filter, receive_file)
    )

    application.add_error_handler(error_handler)

    logging.info("File sharing bot started.")
    application.run_polling()


if __name__ == "__main__":
    main()
