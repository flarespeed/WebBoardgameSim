from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import ChatRoom, Message
from channels.db import database_sync_to_async
from django.utils import timezone
import json



class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'chat_%s' % self.room_name
        await self.soft_create()
        if await self.whitelisted():
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()

    @database_sync_to_async
    def soft_create(self):
        if not ChatRoom.objects.filter(name=self.room_name):
            new_room = ChatRoom(name=self.room_name, public=True, admin=self.scope['user'])
            new_room.save()
            new_room.whitelist.add(self.scope['user'])
            new = Message(room=new_room, username='system', content='New room created', time=timezone.now)
            new.save()

    @database_sync_to_async
    def whitelisted(self):
        current_room = ChatRoom.objects.get(name=self.room_name)
        return current_room.public or current_room.whitelist.filter(id=self.scope['user'].id).exists() or current_room.admin == self.scope['user']

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        time, prev = await self.chatHistory(message, self.scope['user'].username)
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'user': self.scope['user'].username,
                'time': time,
                'prev': prev,
                'message': message
            }
        )

    @database_sync_to_async
    def chatHistory(self, message, user):
        current_room = ChatRoom.objects.get(name=self.room_name)
        new = Message(room=current_room, username=user, content=message, time=timezone.now())
        if Message.objects.filter(room=current_room).exists():
            prev = Message.objects.filter(room=current_room).latest('time')
        new.save()
        return new.time, prev


    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        user = event['user']
        prev = event['prev']
        time = event['time']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'user': user,
            'time': time.strftime('%d %b %Y %X %Z'),
            'prev': time.strftime('%d %b %Y %X %Z'),
            'message': message
        }))