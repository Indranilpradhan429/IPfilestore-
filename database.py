from pymongo import MongoClient
import config, time
client = MongoClient(config.MONGO_URL)
db = client["FileStoreUltimate"]
users = db["users"]
files = db["files"]
settings = db["settings"]
tokens = db["tokens"]
refs = db["refs"]

def get_settings():
    s = settings.find_one({"_id": "main"})
    if not s:
        s = {
            "_id": "main",
            "fsub": [],
            "caption": "📁 {filename}\n🔗 @{botusername}",
            "caption_mode": "both",
            "protect": False,
            "autodelete": 15,
            "start_msg": "Hello {name}!",
            "short_api": config.SHORT_API,
            "short_url": config.SHORT_URL,
            "token_mode": True,
            "token_count": 3,
            "custom_buttons": [],
            "thumb_id": None,
            "analytics": {}
        }
        settings.insert_one(s)
    return s

def update_settings(k,v):
    settings.update_one({"_id":"main"}, {"$set":{k:v}}, upsert=True)

def is_premium(uid):
    u = users.find_one({"_id": uid})
    return u and u.get("premium", 0) > time.time()

def add_token(uid, token):
    tokens.insert_one({"uid": uid, "token": token, "time": time.time()})

def count_tokens(uid):
    return tokens.count_documents({"uid": uid, "time": {"$gt": time.time()-86400}})
