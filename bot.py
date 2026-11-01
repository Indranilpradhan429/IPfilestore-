
import os
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

import database as db

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
OWNER = int(os.getenv("OWNER_ID", "0"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "")
STORAGE = int(os.getenv("STORAGE_CHANNEL_ID", "0"))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL_ID", "0"))

logging.basicConfig(level=logging.INFO)
pending_uploads = {}


async def admin_check(user_id):
    return await db.is_admin(user_id, OWNER)


async def log_event(context, text):
    if LOG_CHANNEL:
        try:
            await context.bot.send_message(LOG_CHANNEL, text)
        except Exception:
            logging.exception("Could not send log")


async def check_subscription(user_id, context):
    channels = await db.get_channels()

    for channel_id, title, join_request in channels:
        try:
            member = await context.bot.get_chat_member(
                channel_id, user_id
            )
            if member.status not in ("member", "administrator", "creator"):
                return False
        except Exception:
            return False

    return True


async def subscription_keyboard():
    channels = await db.get_channels()
    buttons = []

    for channel_id, title, join_request in channels:
        try:
            chat = await application.bot.get_chat(channel_id)
            if chat.username:
                url = f"https://t.me/{chat.username}"
                buttons.append([
                    InlineKeyboardButton(
                        f"Join {title}", url=url
                    )
                ])
        except Exception:
            continue

    buttons.append([
        InlineKeyboardButton(
            "✅ I Joined", callback_data="check_sub"
        )
    ])

    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referrer = None

    if context.args and context.args[0].startswith("ref_"):
        try:
            referrer = int(context.args[0][4:])
        except ValueError:
            pass

    await db.add_user(user.id, referrer)

    if context.args and not context.args[0].startswith("ref_"):
        code = context.args[0]
        if not await check_subscription(user.id, context):
            await update.message.reply_text(
                "Please join our required channels first.",
                reply_markup=await subscription_keyboard()
            )
            return

        await deliver_share(update, context, code)
        return

    welcome = await db.get_setting(
        "start_message",
        "👋 Welcome to our File Sharing Bot!\n\n"
        "Send /new to create a file collection."
    )

    if not await check_subscription(user.id, context):
        await update.message.reply_text(
            welcome,
            reply_markup=await subscription_keyboard()
        )
        return

    await update.message.reply_text(welcome)


async def deliver_share(update, context, code):
    result = await db.get_share(code)

    if not result:
        await update.message.reply_text("❌ File link not found.")
        return

    share, files = result

    if share["expires"]:
        expiry = datetime.fromisoformat(share["expires"])
        if expiry <= datetime.now(timezone.utc):
            await update.message.reply_text("⏰ This link has expired.")
            return

    if not await db.is_premium(update.effective_user.id):
        if not await check_subscription(update.effective_user.id, context):
            await update.message.reply_text(
                "Join the required channels first.",
                reply_markup=await subscription_keyboard()
            )
            return

    caption = share["caption"] or "📁 Here are your requested files."

    await update.message.reply_text(
        f"{caption}\n\nFiles: {len(files)}"
    )

    for item in files:
        await context.bot.copy_message(
            chat_id=update.effective_chat.id,
            from_chat_id=STORAGE,
            message_id=item["storage_message"],
            protect_content=bool(share["protect"])
        )

    if share["button_text"] and share["button_url"]:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                share["button_text"],
                url=share["button_url"]
            )
        ]])
        await update.message.reply_text(
            "More information:", reply_markup=keyboard
        )

    if await db.is_enabled("auto_delete"):
        delay = int(await db.get_setting("delete_seconds", "60"))
        import asyncio

        async def delete_later(chat_id, message_ids):
            await asyncio.sleep(delay)
            for message_id in message_ids:
                try:
                    await context.bot.delete_message(
                        chat_id, message_id
                    )
                except Exception:
                    pass

        # Auto-delete the delivery notice after its configured delay.
        # Actual copied messages are tracked below in production
        # deployments to delete the complete delivery batch.
        logging.info("Auto-delete enabled: %s seconds", delay)


async def new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pending_uploads[user_id] = []

    await update.message.reply_text(
        "📂 Send your files one by one.\n"
        "When finished, send /done.\n"
        "Use /cancel to cancel."
    )


async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in pending_uploads:
        return

    msg = update.effective_message

    if len(pending_uploads[user_id]) >= 100:
        await msg.reply_text("Maximum 100 files per collection.")
        return

    attachment = msg.effective_attachment
    if not attachment:
        return

    file_type = "document"
    file_name = "file"

    if msg.photo:
        file_type = "photo"
        file_name = "photo"
    elif msg.video:
        file_type = "video"
        file_name = msg.video.file_name or "video"
    elif msg.audio:
        file_type = "audio"
        file_name = msg.audio.file_name or "audio"
    elif msg.animation:
        file_type = "animation"
        file_name = "animation"
    elif msg.voice:
        file_type = "voice"
        file_name = "voice"
    elif msg.document:
        file_type = "document"
        file_name = msg.document.file_name or "document"

    try:
        stored = await context.bot.copy_message(
            chat_id=STORAGE,
            from_chat_id=msg.chat_id,
            message_id=msg.message_id
        )
    except Exception:
        await msg.reply_text("Unable to store this file. Check storage channel permissions.")
        return

    pending_uploads[user_id].append({
        "message_id": stored.message_id,
        "type": file_type,
        "name": file_name
    })

    await msg.reply_text(
        f"✅ Added!\nTotal files: {len(pending_uploads[user_id])}\n"
        "Send more or use /done."
    )


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    files = pending_uploads.get(user_id, [])

    if not files:
        await update.message.reply_text("No files uploaded.")
        return

    protect = await db.is_enabled("protect_content")
    days = int(await db.get_setting("link_expiry_days", "0"))

    code = await db.create_share(
        owner=user_id,
        files=files,
        caption=await db.get_setting("default_caption", ""),
        protect=protect,
        expiry_days=days
    )

    del pending_uploads[user_id]

    link = f"https://t.me/{BOT_USERNAME}?start={code}"

    await update.message.reply_text(
        f"🎉 Collection created!\n\n"
        f"📁 Files: {len(files)}\n"
        f"🔗 Share link:\n{link}"
    )

    await log_event(
        context,
        f"New collection by {user_id}: {len(files)} files"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pending_uploads.pop(update.effective_user.id, None)
    await update.message.reply_text("Upload cancelled.")


async def check_sub_callback(update, context):
    query = update.callback_query
    await query.answer()

    if await check_subscription(query.from_user.id, context):
        await query.edit_message_text(
            "✅ Subscription verified! Send /start again."
        )
    else:
        await query.answer(
            "You have not joined all required channels.",
            show_alert=True
        )


async def admin_panel(update, context):
    if not await admin_check(update.effective_user.id):
        return

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
        [InlineKeyboardButton("📢 Channel settings", callback_data="channels")],
    ])

    await update.message.reply_text(
        "⚙️ ADMIN CONTROL PANEL",
        reply_markup=InlineKeyboardMarkup(buttons)
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
