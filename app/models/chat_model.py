# from models.db_client import MongoDBClient
from app.database import Database


class Chat:
    def __init__(self):
        self.db = Database.initialize()
        self.messages_collection = self.db["messages"]
        self.groups_collection = self.db["groups"]
        self.users_collection = self.db["users"]
        self.rooms_collection = self.db["rooms"]

    def get_rooms(self):
        init_room = self.rooms_collection.find_one({"init_room": True})
        return init_room

    def add_to_room(self, room_id, user_id):
        self.rooms_collection.update_one(
            {"_id": room_id}, {"$addToSet": {"members": user_id}}
        )

    def add_message(self, sender, receiver, message_content, message_type):
        self.messages_collection.insert_one(
            {
                "sender": sender,
                "receiver": receiver,
                "message": message_content,
                "type": message_type,
            }
        )

    def create_group(self, group_name, creator):
        self.groups_collection.insert_one({"name": group_name, "members": [creator]})

    def add_to_group(self, group_name, member):
        self.groups_collection.update_one(
            {"name": group_name}, {"$addToSet": {"members": member}}
        )

    def add_friend(self, username, friend_name):
        self.users_collection.update_one(
            {"username": username}, {"$addToSet": {"friends": friend_name}}
        )

    def list_friends(self, username):
        user = self.users_collection.find_one({"username": username})
        return user.get("friends", [])

    def list_groups(self, username):
        user_groups = self.groups_collection.find({"members": username})
        return [group["name"] for group in user_groups]

    def set_user_status(self, username, status):
        self.users_collection.update_one(
            {"username": username}, {"$set": {"status": status}}
        )

    def get_group_members(self, group_name):
        group = self.groups_collection.find_one({"name": group_name})
        return group["members"] if group else []
