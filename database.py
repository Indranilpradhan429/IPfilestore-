from pymongo import MongoClient
import os
MONGO = os.environ.get("MONGO_URL") or os.environ.get("DB_URI")
client = MongoClient(MONGO)
db = client["vjbot"]
settings = db["settings"]
files = db["files"]
batches = db["batches"]

def get_set():
    s = settings.find_one({"_id":"main"})
    if not s:
        s = {
            "_id":"main",
            "protect": False,  # False = Copy ON
            "autodelete": 0,
            "fsub": [],
            "caption": "🎬 {file_name}\n\nJoin @YourChannel",
            "short_on": False,
            "verify_on": False,
            "db_channel": 0
        }
        settings.insert_one(s)
    return s

def update(k,v):
    settings.update_one({"_id":"main"}, {"$set":{k:v}}, upsert=True)
