from pydantic import BaseModel


class WebSocketMessage(BaseModel):
	type: str
	user_email: str
	content: dict
