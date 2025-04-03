import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.controllers.websocket_controller import WebSocketManager

router = APIRouter()
websocket_manager = WebSocketManager()


@router.websocket('/{room_id}')
async def websocket_endpoint(websocket: WebSocket, room_id: str):
	await websocket_manager.connect_websocket(websocket, room_id)
	try:
		while True:
			data = await websocket.receive_text()
			message = json.loads(data)
			# message = WebSocketMessage(**json.loads(data))
			await websocket_manager.handle_message(websocket, message, room_id)
	except WebSocketDisconnect:
		await websocket_manager.disconnect_websocket(room_id, message)
