import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
import aioredis
import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379")

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.partner = None
        self.redis = await aioredis.from_url(REDIS_URL)
        self.channel_layer = get_channel_layer()

        await self.redis.lpush("waiting_users", self.channel_name)
        await self.try_pair()

    async def disconnect(self, close_code):
        if self.partner:
            await self.channel_layer.send(self.partner, {
                "type": "leave.chat"
            })
        else:
            await self.redis.lrem("waiting_users", 0, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data["type"] == "message" and self.partner:
            await self.channel_layer.send(self.partner, {
                "type": "chat.message",
                "message": data["message"]
            })

        elif data["type"] == "next":
            await self.disconnect(1000)
            await self.connect()

        elif data["type"] == "typing" and self.partner:
            await self.channel_layer.send(self.partner, {
                "type": "typing"
            })

    async def try_pair(self):
        while True:
            other = await self.redis.rpop("waiting_users")
            if not other:
                return
            other = other.decode()

            if other != self.channel_name:
                self.partner = other
                await self.channel_layer.send(other, {
                    "type": "start.chat",
                    "partner": self.channel_name
                })
                await self.send(text_data=json.dumps({"type": "connected"}))
                return

    async def start_chat(self, event):
        self.partner = event["partner"]
        await self.send(text_data=json.dumps({"type": "connected"}))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "message",
            "message": event["message"]
        }))

    async def leave_chat(self, event):
        await self.send(text_data=json.dumps({
            "type": "leave"
        }))

    async def typing(self, event):
        await self.send(text_data=json.dumps({
            "type": "typing"
        }))
