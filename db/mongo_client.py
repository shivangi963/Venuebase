import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

load_dotenv()

_client = None

def get_client():
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise ValueError("MONGODB_URI not set in .env file")
        _client = MongoClient(uri)
        try:
            _client.admin.command("ping")
        except ConnectionFailure:
            raise ConnectionFailure("Could not connect to MongoDB. Check your MONGODB_URI.")
    return _client


def get_db():
    client = get_client()
    db_name = os.getenv("MONGODB_DB_NAME", "venue_rfp")
    return client[db_name]


#  Collection helpers 

def get_users_collection():
    return get_db()["users"]


def get_projects_collection():
    return get_db()["rfp_projects"]


# Index setup 

def ensure_indexes():
    users_col = get_users_collection()
    users_col.create_index("username", unique=True)
    users_col.create_index("email", unique=True)

    projects_col = get_projects_collection()
    projects_col.create_index("user_id")