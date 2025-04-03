import datetime
import json
from typing import Dict, List

from bson import ObjectId
from fastapi import WebSocket
from pymongo import UpdateOne

from app.database import Database


class WebSocketManager:
	def __init__(self):
		self.connected_clients: Dict[str, WebSocket] = {}
		self.rooms: Dict[str, List[WebSocket]] = {}
		self.db = Database.get_db()
		self.users_collection = Database.get_users_collection()
		self.messages_collection = Database.get_messages_collection()
		self.rooms_collection = Database.get_rooms_collection()
		self.friends_collection = Database.get_friends_collection()

	async def connect_websocket(self, websocket: WebSocket, room_id: str):
		await websocket.accept()
		if room_id not in self.rooms:
			self.rooms[room_id] = []
		self.rooms[room_id].append(websocket)

	async def disconnect_websocket(self, room_id: str, data):
		websocket = self.connected_clients.pop(data.get('user_email'), None)
		if websocket and room_id in self.rooms:
			self.rooms[room_id].remove(websocket)
			if not self.rooms[room_id]:
				del self.rooms[room_id]

	async def broadcast_message(self, message: str, room_id: str):
		for websocket in self.rooms[room_id]:
			await websocket.send_text(json.dumps(message))

	async def handle_message(self, websocket: WebSocket, data, room_id: str):
		self.connected_clients[data.get('user_email')] = websocket
		await self.switch(data, websocket, room_id)

	# 判斷傳入類型
	async def switch(self, data, websocket, room_id):
		match data['type']:
			case 'message':
				await self.send_message(data, websocket, room_id)
			case 'create_room':
				await self.create_room(data, websocket)
			case 'invite_to_room':
				await self.invite_to_room(data, websocket)
			case 'get_history':
				await self.send_history(data, websocket, room_id)
			case 'get_lists':
				await self.send_lists(data, websocket)
			case 'add_friend':
				await self.add_friend(data, websocket)
			case 'remove_friend':
				await self.remove_friend(data, websocket)
			case _:
				print(f'未定義類型 : {data["type"]}')

	# 傳送訊息
	async def send_message(self, data, websocket, room_id):
		now = datetime.datetime.now(
			tz=datetime.timezone(datetime.timedelta(hours=8))
		).strftime('%Y/%m/%d %H:%M:%S')

		message = {'author': data['author'], 'content': data['content'], 'time': now}

		await self.rooms_collection.find_one({'_id': ObjectId(room_id)})
		await self.rooms_collection.update_one(
			{'_id': ObjectId(room_id)},
			{'$push': {'messages': message}},
		)

		response = {'type': 'message'} | message
		for user in self.rooms[room_id]:
			await user.send_text(json.dumps(response))

	# 建立聊天室
	async def create_room(self, data, websocket):
		user = await self.users_collection.find_one({'email': data['creator_id']})

		room = {
			'name': data['room_name'],
			'created_by': ObjectId(user['_id']),
			'members': [{'_id': str(user['_id']), 'member_name': user['username']}],
			'room_type': 'group',
			'messages': [],
		}

		# room_id = await self.rooms_collection.insert_one(room).inserted_id
		room_id = await self.rooms_collection.insert_one(room)
		await self.users_collection.update_one(
			{'_id': ObjectId(user['_id'])},
			{
				'$push': {
					'rooms': {
						'room_id': str(room_id.inserted_id),
						'room_name': data['room_name'],
						'room_type': 'group',
					}
				}
			},
		)

		await websocket.send_text(
			json.dumps(
				{
					'type': 'room_created',
					'room_name': data['room_name'],
					'room_id': str(room_id.inserted_id),
					'room_type': 'group',
					'message': '聊天室建立成功！',
				}
			)
		)

	# 邀請到房間
	async def invite_to_room(self, data, websocket):
		friend_id = data['friend_id']
		friend_name = data['friend_name']
		friend_email = data['friend_email']
		room_id = data['room_id']
		room_name = data['room_name']

		user_requests = [
			UpdateOne(
				{'_id': ObjectId(friend_id)},
				{
					'$addToSet': {
						'rooms': {
							'room_id': room_id,
							'room_name': room_name,
							'room_type': 'group',
						}
					}
				},
			),
		]

		room_requests = [
			UpdateOne(
				{'_id': ObjectId(room_id)},
				{'$addToSet': {'members': [{'_id': friend_id, 'member_name': friend_name}]}},
			),
		]

		response = {
			'type': 'invited_to_room',
			'friend_id': friend_id,
			'friend_name': friend_name,
			'room_id': room_id,
			'room_name': room_name,
			'room_type': 'group',
		}
		await self.users_collection.bulk_write(user_requests)
		await self.rooms_collection.bulk_write(room_requests)
		if friend_email in self.connected_clients:
			await self.connected_clients[friend_email].send_text(json.dumps(response))

	# 取得歷史訊息
	async def send_history(self, data, websocket, room_id):
		room_id = ObjectId(room_id)
		room = await self.rooms_collection.find_one({'_id': room_id})
		messages = room.get('messages')
		members = room.get('members')
		await websocket.send_text(
			json.dumps({'type': 'history', 'messages': messages, 'members': members})
		)

	# 取得清單
	async def send_lists(self, data, websocket):
		user_email = data.get('user_email')
		user = await self.users_collection.find_one({'email': user_email})
		chatLists = user['rooms']
		friendLists = user['friends']
		response = {
			'type': 'list_update',
			'chatLists': chatLists,
			'friendLists': friendLists,
		}
		await websocket.send_text(json.dumps(response))

	# 加入好友
	async def add_friend(self, data, websocket):
		user_email = data['user_email']
		friend_email = data['friend_email']

		user = await self.users_collection.find_one({'email': user_email})
		friend = await self.users_collection.find_one({'email': friend_email})

		friend_ids = {friend['friend_id'] for friend in user['friends']}
		old_friend_ids = {friend['friend_id'] for friend in friend['friends']}
		exists = str(friend['_id']) in friend_ids
		if exists:
			response = {'type': 'friend_existed', 'friend_id': str(friend['_id'])}
			await websocket.send_text(json.dumps(response))

		elif str(user['_id']) in old_friend_ids:
			old_room_id = {
				'room_id': friend['friend_room_id']
				for friend in friend['friends']
				if friend['friend_id'] == str(user['_id'])
			}
			await self.users_collection.update_one(
				{'_id': user['_id']},
				{
					'$addToSet': {
						'friends': {
							'friend_id': str(friend['_id']),
							'friend_name': friend['username'],
							'friend_room_id': old_room_id['room_id'],
							'friend_email': friend_email,
						},
						'rooms': {
							'room_id': old_room_id['room_id'],
							'room_name': friend['username'],
							'room_type': 'friend',
						},
					}
				},
			)
			response = {
				'type': 'friend_added',
				'friend_id': str(friend['_id']),
				'friend_email': friend_email,
				'friend_name': friend['username'],
				'friend_room_id': old_room_id['room_id'],
			}
			await websocket.send_text(json.dumps(response))

		elif user and friend:
			room = {
				'name': f'{user.get("username")} and {friend.get("username")} room',
				'created_by': ObjectId(user['_id']),
				'room_type': 'friend',
				'members': [
					{'_id': str(user['_id']), 'member_name': user['username']},
					{'_id': str(friend['_id']), 'member_name': friend['username']},
				],
				'messages': [],
			}
			room_id = await self.rooms_collection.insert_one(room).inserted_id
			await self.users_collection.update_one(
				{'_id': friend['_id']},
				{
					'$addToSet': {
						'friends': {
							'friend_id': str(user['_id']),
							'friend_name': user['username'],
							'friend_room_id': str(room_id),
							'friend_email': user_email,
						},
						'rooms': {
							'room_id': str(room_id),
							'room_name': user['username'],
							'room_type': 'friend',
						},
					}
				},
			)
			await self.users_collection.update_one(
				{'_id': user['_id']},
				{
					'$addToSet': {
						'friends': {
							'friend_id': str(friend['_id']),
							'friend_name': friend['username'],
							'friend_room_id': str(room_id),
							'friend_email': friend_email,
						},
						'rooms': {
							'room_id': str(room_id),
							'room_name': friend['username'],
							'room_type': 'friend',
						},
					}
				},
			)

			response = {
				'type': 'friend_added',
				'friend_id': str(friend['_id']),
				'friend_email': friend_email,
				'friend_name': friend['username'],
				'friend_room_id': str(room_id),
			}
			response_to_friend = {
				'type': 'friend_added',
				'friend_id': str(user['_id']),
				'friend_email': user_email,
				'friend_name': user['username'],
				'friend_room_id': str(room_id),
			}

			if friend_email in self.connected_clients:
				await self.connected_clients[friend_email].send_text(
					json.dumps(response_to_friend)
				)
			await websocket.send_text(json.dumps(response))

		else:
			response = {'type': 'friend_not_found', 'friend_email': friend_email}
			await websocket.send_text(json.dumps(response))

	# 移除好友
	async def remove_friend(self, data, websocket):
		user_email = data['user_email']
		friend_id = data['friend_id']
		user = await self.users_collection.find_one({'email': user_email})
		user_requests = [
			UpdateOne({'_id': user['_id']}, {'$pull': {'friends': {'friend_id': friend_id}}}),
			UpdateOne(
				{'_id': user['_id']},
				{'$pull': {'rooms': {'room_id': data['friend_room_id']}}},
			),
		]
		response = {
			'type': 'friend_removed',
			'friend_id': friend_id,
			'friend_room_id': data['friend_room_id'],
		}

		await self.users_collection.bulk_write(user_requests)
		await websocket.send_text(json.dumps(response))
