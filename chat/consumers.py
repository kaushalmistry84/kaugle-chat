# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

connected_users = []

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.partner = None
        connected_users.append(self)
        await self.try_pair()

    async def disconnect(self, close_code):
        if self.partner:
            await self.partner.send(text_data=json.dumps({"type": "leave"}))
            self.partner.partner = None
        if self in connected_users:
            connected_users.remove(self)

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data["type"] == "message" and self.partner:
            await self.partner.send(text_data=json.dumps({
                "type": "message",
                "message": data["message"]
            }))

        elif data["type"] == "next":
            await self.disconnect(1000)
            await self.connect()

        elif data["type"] == "typing" and self.partner:
            await self.partner.send(text_data=json.dumps({
                "type": "typing"
            }))

    async def try_pair(self):
        for user in connected_users:
            if user != self and user.partner is None:
                self.partner = user
                user.partner = self
                await self.send(text_data=json.dumps({"type": "connected"}))
                await user.send(text_data=json.dumps({"type": "connected"}))
                break
