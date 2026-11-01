import os
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DB_CHANNEL = int(os.environ.get("DB_CHANNEL", "0"))
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "0"))
SHORT_API = os.environ.get("SHORT_API", "")
SHORT_URL = os.environ.get("SHORT_URL", "api.shareus.io")
