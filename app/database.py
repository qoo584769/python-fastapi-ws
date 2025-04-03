import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi

# 加載環境變數
load_dotenv()


class Database:
	_client = None
	_db = None
	_users_collection = None
	_messages_collection = None
	_rooms_collection = None
	_friends_collection = None

	@classmethod
	def initialize(cls):
		"""初始化 MongoDB 連線"""
		if cls._client is None:
			# MongoDB 的連線 URI
			MONGO_URI = os.getenv('MONGO_URI')
			# 資料庫名稱
			MONGO_DATABASE = os.getenv('MONGO_DATABASE')

			try:
				cls._client = AsyncIOMotorClient(MONGO_URI, server_api=ServerApi('1'))
				cls._db = cls._client[MONGO_DATABASE]
				cls._users_collection = cls._db.users
				cls._messages_collection = cls._db.messages
				cls._rooms_collection = cls._db.rooms
				cls._friends_collection = cls._db.friends

				# 測試連線
				cls._client.admin.command('ping')
				print('MongoDB 連線成功！')
			except Exception as e:
				print(f'MongoDB 連線失敗：{e}')
				cls._client = None
				cls._db = None

	@classmethod
	def get_db(cls):
		"""獲取資料庫物件"""
		if cls._db is None:
			cls.initialize()
		return cls._db

	@classmethod
	def get_users_collection(cls):
		if cls._db is None:
			cls.initialize()
		return cls._users_collection

	@classmethod
	def get_messages_collection(cls):
		if cls._db is None:
			cls.initialize()
		return cls._messages_collection

	@classmethod
	def get_rooms_collection(cls):
		if cls._db is None:
			cls.initialize()
		return cls._rooms_collection

	@classmethod
	def get_friends_collection(cls):
		if cls._db is None:
			cls.initialize()
		return cls._friends_collection
