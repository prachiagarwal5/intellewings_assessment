from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client["iosco_database"]
profiles_collection = db["profiles"]
checkpoint_collection = db["checkpoint"]
