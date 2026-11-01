import os
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
ADMIN_ID = int(os.environ.get("8138159606", "0"))
DB_CHANNEL = int(os.environ.get("1003240202146", "0"))
LOG_CHANNEL = int(os.environ.get("1003240202146", "0"))
SHORT_API = os.environ.get("SHORT_API", "")
SHORT_URL = os.environ.get("SHORT_URL", "api.shareus.io")
