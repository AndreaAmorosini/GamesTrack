import os
from pymongo import MongoClient

MONGO_URI = f"mongodb://{os.getenv('MONGO_INIT_USER')}:{os.getenv('MONGO_INIT_PASS')}@mongo:27017/"


def get_db():
    client = MongoClient(MONGO_URI)
    db = client["game_tracker"]
    try:
        yield db
    finally:
        client.close()
