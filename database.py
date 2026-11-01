from pymongo import MongoClient
import config
client = MongoClient(config.MONGO_URL)
db = client["filterbot"]
files = db["files"]
settings_col = db["settings"]

def get_settings():
    s = settings_col.find_one({"_id": "settings"})
    if not s:
        s = {"_id": "settings", "short_api": "", "short_url": "shrinkme.io", "protect": False, "autodelete": 0, "fsub": [], "caption": "📁 {filename}"}
        settings_col.insert_one(s)
    return s

def update_settings(k, v):
    settings_col.update_one({"_id": "settings"}, {"$set": {k: v}}, upsert=True)
