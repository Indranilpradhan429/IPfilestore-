
import aiosqlite
import os
import json
import secrets
from datetime import datetime, timedelta, timezone

DB_PATH = os.getenv("DATABASE_PATH", "bot.db")


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            referred_by INTEGER,
            joined TEXT
        );

        CREATE TABLE IF NOT EXISTS shares (
            code TEXT PRIMARY KEY,
            owner INTEGER,
            created TEXT,
            expires TEXT,
            caption TEXT,
            thumbnail TEXT,
            button_text TEXT,
            button_url TEXT,
            protect INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            storage_message INTEGER,
            file_type TEXT,
            file_name TEXT
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS channels (
            channel_id INTEGER PRIMARY KEY,
            title TEXT,
            join_request INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS premium (
            user_id INTEGER PRIMARY KEY,
            expires TEXT
        );

        CREATE TABLE IF NOT EXISTS referrals (
            user_id INTEGER PRIMARY KEY,
            invited_by INTEGER
        );

        CREATE TABLE IF NOT EXISTS verifications (
            user_id INTEGER PRIMARY KEY,
            token1 INTEGER DEFAULT 0,
            token2 INTEGER DEFAULT 0,
            token3 INTEGER DEFAULT 0,
            expires TEXT
        );

        CREATE TABLE IF NOT EXISTS shortener_tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER,
            step INTEGER,
            expires TEXT,
            used INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS user_sessions (
            user_id INTEGER PRIMARY KEY,
            caption TEXT DEFAULT '',
            thumbnail TEXT DEFAULT '',
            button_text TEXT DEFAULT '',
            button_url TEXT DEFAULT '',
            auto_delete INTEGER DEFAULT 0
        );
        """)
        await db.commit()


async def get_setting(key, default=""):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else default


async def set_setting(key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO settings(key,value) VALUES(?,?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            (key, str(value))
        )
        await db.commit()


async def is_enabled(key):
    return (await get_setting(key, "off")) == "on"


async def create_share(owner, files, caption="", thumbnail="",
                       button_text="", button_url="",
                       protect=False, expiry_days=0):
    code = secrets.token_urlsafe(9)
    now = datetime.now(timezone.utc)

    expires = (
        (now + timedelta(days=expiry_days)).isoformat()
        if expiry_days else None
    )

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO shares
            (code,owner,created,expires,caption,thumbnail,
             button_text,button_url,protect)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (code, owner, now.isoformat(), expires, caption,
             thumbnail, button_text, button_url, int(protect))
        )

        for item in files:
            await db.execute(
                """INSERT INTO files
                (code,storage_message,file_type,file_name)
                VALUES(?,?,?,?)""",
                (code, item["message_id"],
                 item["type"], item["name"])
            )

        await db.commit()

    return code


async def get_share(code):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM shares WHERE code=?", (code,)
        ) as cur:
            share = await cur.fetchone()

        if not share:
            return None

        async with db.execute(
            "SELECT * FROM files WHERE code=?", (code,)
        ) as cur:
            files = await cur.fetchall()

        return dict(share), [dict(f) for f in files]


async def add_user(user_id, referrer=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users VALUES(?,?,?)",
            (user_id, referrer,
             datetime.now(timezone.utc).isoformat())
        )
        if referrer and referrer != user_id:
            await db.execute(
                "INSERT OR IGNORE INTO referrals VALUES(?,?)",
                (user_id, referrer)
            )
        await db.commit()


async def set_premium(user_id, days):
    expiry = (
        datetime.now(timezone.utc) +
        timedelta(days=days)
    ).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO premium VALUES(?,?)
            ON CONFLICT(user_id) DO UPDATE SET expires=excluded.expires""",
            (user_id, expiry)
        )
        await db.commit()


async def is_premium(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT expires FROM premium WHERE user_id=?",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()

    return bool(
        row and datetime.fromisoformat(row[0]) >
        datetime.now(timezone.utc)
    )


async def add_channel(channel_id, title, join_request=False):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO channels
            VALUES(?,?,?)""",
            (channel_id, title, int(join_request))
        )
        await db.commit()


async def get_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT channel_id,title,join_request FROM channels"
        ) as cur:
            return await cur.fetchall()


async def get_admins(owner_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM admins"
        ) as cur:
            rows = await cur.fetchall()

    return {owner_id} | {r[0] for r in rows}


async def is_admin(user_id, owner_id):
    return user_id in await get_admins(owner_id)


async def add_admin(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO admins VALUES(?)", (user_id,)
        )
        await db.commit()


async def remove_admin(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM admins WHERE user_id=?", (user_id,)
        )
        await db.commit()
