from pymongo import MongoClient
import config
client = MongoClient(config.MONGO_URL)
db = client["prostorebot"]
files_col = db["files"]
batches_col = db["batches"]
users_col = db["users"]
settings_col = db["settings"]

def get_settings():
    s = settings_col.find_one({"_id":"main"})
    if not s:
        s = {"_id":"main","protect":False,"autodelete":0,"fsub":[],"caption":"","button":"","start_msg":"👋 Hi {name}\nBot Live ✅","short_on":False,"verify_on":False,"verify_tokens":3,"db_channel":0,"refer_bonus":10}
        settings_col.insert_one(s)
    return s
def update_settings(k,v):
    settings_col.update_one({"_id":"main"}, {"$set":{k:v}}, upsert=True)
def save_file(fid, mid, caption=""):
    files_col.update_one({"file_id":fid}, {"$set":{"msg_id":mid,"caption":caption}}, upsert=True)
def get_file(fid):
    return files_col.find_one({"file_id":fid})
def save_batch(bid, mids, captions):
    batches_col.update_one({"batch_id":bid}, {"$set":{"mids":mids,"captions":captions}}, upsert=True)
def get_batch(bid):
    return batches_col.find_one({"batch_id":bid})
def add_user(uid):
    if not users_col.find_one({"_id":uid}):
        users_col.insert_one({"_id":uid})
