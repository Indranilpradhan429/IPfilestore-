from pymongo import MongoClient
import config

client = MongoClient(config.MONGO_URL)
db = client["filterbot"]
files_col = db["files"]
settings_col = db["settings"]

def get_settings():
    s = settings_col.find_one({"_id": "settings"})
    if not s:
        s = {
            "_id": "settings",
            "short_api": config.SHORT_API,
            "short_url": config.SHORT_URL,
            "protect": False,
            "autodelete": 0,
            "fsub": [],
            "caption": "📁 {filename}",
            "shortlink": False
        }
        settings_col.insert_one(s)
    return s

def update_settings(k, v):
    settings_col.update_one({"_id": "settings"}, {"$set": {k: v}}, upsert=True)

def save_file(file_id, msg_id):
    files_col.update_one({"file_id": file_id}, {"$set": {"msg_id": msg_id}}, upsert=True)

def get_file(file_id):
    return files_col.find_one({"file_id": file_id})
