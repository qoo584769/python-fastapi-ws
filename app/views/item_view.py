from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.controllers import item_controller
from app.models.item import Item

router = APIRouter()
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage2(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/123");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
            function sendMessage2(event) {
                var input = document.getElementById("messageText")
                let message1 = {type: 'chat',
                    user_email: 'user1@gmail.com',
                    content: {user:'user1',message:input.value}}
                ws.send(JSON.stringify(message1))
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@router.get('/')
def get():
	return HTMLResponse(html)


@router.get('/items/')
def read_items():
	return item_controller.get_items()


@router.get('/items/{item_id}')
def read_item(item_id: int):
	return item_controller.get_item(item_id)


@router.post('/items/')
def create_item(item: Item):
	return item_controller.create_item(item)
