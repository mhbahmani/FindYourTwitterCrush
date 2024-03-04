# mongo client methos
from decouple import config
from pymongo import MongoClient


class DB:
    def __init__(self) -> None:
        self.client = MongoClient(
            config("MONGO_HOST", "localhost"),
            config("MONGO_PORT", 27017, cast=int)
        )
        self.db = self.client[config("MONGO_DB", "twitter")]
    
    def add_handled_liking(self, user: dict) -> None:
        """
        user: {
            username: str,
            result: []
        }
        """
        self.db.liking.insert_one(user)

    def add_handled_liked(self, user: dict) -> None:
        """
        user: {
            username: str,
            result: []
        }
        """
        self.db.liked.insert_one(user)
    
    def get_all_handled_liking(self) -> list:
        return [user.get("username") for user in list(self.db.liking.find({}, {"username": 1, "_id": 0}))]
        
    def get_all_handled_liked(self) -> list:
        return [user.get("username") for user in list(self.db.liked.find({}, {"username": 1, "_id": 0}))]
        