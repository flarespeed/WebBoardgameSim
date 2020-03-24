from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import GameRoom, BoardTemplate, Move, GameMessage
from channels.db import database_sync_to_async
from django.utils import timezone
import json



class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'games_%s' % self.room_name
        if await self.roomExists() and await self.whitelisted():
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()

    @database_sync_to_async
    def roomExists(self):
        return GameRoom.objects.filter(name=self.room_name).exists()

    @database_sync_to_async
    def whitelisted(self):
        current_room = GameRoom.objects.get(name=self.room_name)
        return current_room.whitelist.filter(id=self.scope['user'].id).exists() or current_room.admin == self.scope['user']

    async def receive(self, text_data):
        data = json.loads(text_data)
        if 'type' in data:
            content = data['content']
            if data['type'] == 'message':
                print('got message')
                time, prev = await self.messageHistory(content['message'], self.scope['user'].username)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'game_message',
                        'user': self.scope['user'].username,
                        'time': time,
                        'prev': prev,
                        'message': content['message']
                    }
                )
            if data['type'] == 'move':
                print('got move')
                time, prev = await self.moveHistory(content, self.scope['user'].username)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'game_move',
                        'user': self.scope['user'].username,
                        'time': time,
                        'prev': prev,
                        'move': content,
                    }
                )

    @database_sync_to_async
    def messageHistory(self, message, user):
        current_room = GameRoom.objects.get(name=self.room_name)
        new = GameMessage(room=current_room, username=user, content=message, time=timezone.now())
        if GameMessage.objects.filter(room=current_room).exists():
            prev = GameMessage.objects.filter(room=current_room).latest('time')
        else:
            prev = timezone.now()
        new.save()
        return new.time, prev

    @database_sync_to_async
    def moveHistory(self, content, user):
        current_room = GameRoom.objects.get(name=self.room_name)
        new = Move(room=current_room, username=user, content=json.dumps(content), time=timezone.now())
        if Move.objects.filter(room=current_room).exists():
            prev = Move.objects.filter(room=current_room).latest('time')
        else:
            prev = timezone.now()
        new.save()
        board = json.loads(current_room.board_state)
        off_board = json.loads(current_room.off_board)
        if content['from']['i'] == -1:
            board[content['to']['i']]['pieces'].insert(0, off_board[content['piece']])
        elif content['to']['i'] == -1:
            if content['piece'] > -1:
                piece = board[content['from']['i']]['pieces'].pop(content['piece'])
                if piece not in off_board:
                    off_board.insert(0, piece)
            else:
                stack = board[content['from']['i']]['pieces']
                for item in board[content['from']['i']]['pieces']:
                    board[content['from']['i']]['pieces'].remove(item)
                for i in range(len(stack)):
                    if stack[i] not in off_board:
                        off_board.insert(i, stack[i])
        else:
            if content['piece'] > -1:
                piece = board[content['from']['i']]['pieces'].pop(content['piece'])
                board[content['to']['i']]['pieces'].insert(0, piece)
            else:
                stack = board[content['from']['i']]['pieces']
                for item in board[content['from']['i']]['pieces']:
                    board[content['from']['i']]['pieces'].remove(item)
                for i in range(len(stack)):
                    board[content['to']['i']]['pieces'].insert(i, stack[i])
        current_room.off_board = json.dumps(off_board)
        current_room.board_state = json.dumps(board)
        current_room.save()

        return new.time, prev

    async def game_message(self, event):
        message = event['message']
        user = event['user']
        prev = event['prev']
        time = event['time']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'content': {
                'user': user,
                'time': time.strftime('%d %b %Y %X %Z'),
                'prev': time.strftime('%d %b %Y %X %Z'),
                'message': message
            }
        }))

    async def game_move(self, event):
        move = event['move']
        print(move)
        user = event['user']
        prev = event['prev']
        time = event['time']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'move',
            'content': {
                'user': user,
                'time': time.strftime('%d %b %Y %X %Z'),
                'prev': time.strftime('%d %b %Y %X %Z'),
                'piece': move['piece'],
                'from': move['from'],
                'to': move['to']
            }
        }))