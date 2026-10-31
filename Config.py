import os
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_CHANNEL = int(os.getenv("DB_CHANNEL", "0"))
SHORT_API = os.getenv("SHORT_API", "")
SHORT_URL = os.getenv("SHORT_URL", "shrinkme.io")
