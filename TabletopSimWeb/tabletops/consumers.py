from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import GameRoom, BoardTemplate, Move, GameMessage
from django.contrib.auth.models import User
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
            if data['type'] == 'kick':
                if await self.remove_from_whitelist(content['kickee']):
                    time = timezone.now()
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'kick_user',
                            'user': self.scope['user'].username,
                            'time': time,
                            'kickee': content['kickee'],
                            'reason': content['reason']
                        }
                    )
            if data['type'] == 'piece_create':
                message = self.scope['user'].username + ' created new piece.'
                time, prev = await self.create_new_piece(content, message)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'piece_create',
                        'user': self.scope['user'].username,
                        'time': time,
                        'prev': prev,
                        'piece': content,
                        'message': message
                    }
                )
            if data['type'] == 'piece_edit':
                time, prev, message = await self.edit_piece(content)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'piece_edit',
                        'user': self.scope['user'].username,
                        'time': time,
                        'prev': prev,
                        'piece': content['piece'],
                        'to': content['to'],
                        'message': message
                    }
                )
            if data['type'] == 'piece_delete':
                time, prev, message = await self.delete_piece(content)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'piece_delete',
                        'user': self.scope['user'].username,
                        'time': time,
                        'prev': prev,
                        'piece': content['piece'],
                        'message': message
                    }
                )

    @database_sync_to_async
    def create_new_piece(self, content, message):
        current_room = GameRoom.objects.get(name=self.room_name)
        off_board = json.loads(current_room.off_board)
        off_board.append(content)
        current_room.off_board = json.dumps(off_board)
        current_room.save()
        new = GameMessage(room=current_room, username='system', content=message, time=timezone.now())
        if GameMessage.objects.filter(room=current_room).exists():
            prev = GameMessage.objects.filter(room=current_room).latest('time').time
        else:
            prev = timezone.now()
        new.save()
        return new.time, prev

    @database_sync_to_async
    def edit_piece(self, content):
        current_room = GameRoom.objects.get(name=self.room_name)
        off_board = json.loads(current_room.off_board)
        old = off_board[content['piece']]
        message = self.scope['user'].username + ' changed ' + old['name'] + ' to ' + content['to']['name'] + '.'
        off_board[content['piece']]['name']=content['to']['name']
        off_board[content['piece']]['img']=content['to']['img']
        current_room.off_board = json.dumps(off_board)
        current_room.save()
        new = GameMessage(room=current_room, username='system', content=message, time=timezone.now())
        if GameMessage.objects.filter(room=current_room).exists():
            prev = GameMessage.objects.filter(room=current_room).latest('time').time
        else:
            prev = timezone.now()
        new.save()
        return new.time, prev, message

    @database_sync_to_async
    def delete_piece(self, content):
        current_room = GameRoom.objects.get(name=self.room_name)
        off_board = json.loads(current_room.off_board)
        old = off_board.pop(content['piece'])
        current_room.off_board = json.dumps(off_board)
        current_room.save()
        message = self.scope['user'].username + ' deleted ' + old['name']
        new = GameMessage(room=current_room, username='system', content=message, time=timezone.now())
        if GameMessage.objects.filter(room=current_room).exists():
            prev = GameMessage.objects.filter(room=current_room).latest('time').time
        else:
            prev = timezone.now()
        new.save()
        return new.time, prev, message

    @database_sync_to_async
    def remove_from_whitelist(self, kickee):
        current_room = GameRoom.objects.get(name=self.room_name)
        if self.scope['user'] != current_room.admin:
            return False
        possUser = User.objects.filter(username=kickee)
        if possUser.exists():
            user = possUser[0]
            if user in current_room.whitelist.all():
                current_room.whitelist.remove(user)
                return True
        return False

    @database_sync_to_async
    def messageHistory(self, message, user):
        current_room = GameRoom.objects.get(name=self.room_name)
        new = GameMessage(room=current_room, username=user, content=message, time=timezone.now())
        if GameMessage.objects.filter(room=current_room).exists():
            prev = GameMessage.objects.filter(room=current_room).latest('time').time
        else:
            prev = timezone.now()
        new.save()
        return new.time, prev

    @database_sync_to_async
    def moveHistory(self, content, user):
        current_room = GameRoom.objects.get(name=self.room_name)
        board = json.loads(current_room.board_state)
        off_board = json.loads(current_room.off_board)
        if content['from']['i'] == -1:
            content['pieceName'] = off_board[content['piece']]['name']
        else:
            content['pieceName'] = board[content['from']['i']]['pieces'][content['piece']]['name']
        new = Move(room=current_room, username=user, content=json.dumps(content), time=timezone.now())
        if Move.objects.filter(room=current_room).exists():
            prev = Move.objects.filter(room=current_room).latest('time').time
        else:
            prev = timezone.now()
        new.save()
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
                board[content['to']['i']]['pieces'] = stack + board[content['to']['i']]['pieces']
        current_room.off_board = json.dumps(off_board)
        current_room.board_state = json.dumps(board)
        current_room.save()

        return new.time, prev


    # each function after this recieves different types of message from the group that they're in
    async def game_message(self, event):
        message = event['message']
        user = event['user']
        prev = event['prev']
        time = event['time']

        await self.send(text_data=json.dumps({
            'type': 'message',
            'content': {
                'user': user,
                'time': time.strftime('%d %b %Y %X %Z'),
                'prev': prev.strftime('%d %b %Y %X %Z'),
                'message': message
            }
        }))

    async def piece_create(self, event):
        message = event['message']
        user = event['user']
        prev = event['prev']
        time = event['time']
        piece = event['piece']

        await self.send(text_data=json.dumps({
            'type': 'piece_create',
            'content': {
                'user': user,
                'time': time.strftime('%d %b %Y %X %Z'),
                'prev': prev.strftime('%d %b %Y %X %Z'),
                'piece': piece,
                'message': message
            }
        }))

    async def piece_edit(self, event):
        message = event['message']
        piece = event['piece']
        to = event['to']
        user = event['user']
        prev = event['prev']
        time = event['time']

        await self.send(text_data=json.dumps({
            'type': 'piece_edit',
            'content': {
                'user': user,
                'time': time.strftime('%d %b %Y %X %Z'),
                'prev': prev.strftime('%d %b %Y %X %Z'),
                'piece': piece,
                'to': to,
                'message': message
            }
        }))

    async def piece_delete(self, event):
        piece = event['piece']
        message = event['message']
        user = event['user']
        prev = event['prev']
        time = event['time']

        await self.send(text_data=json.dumps({
            'type': 'piece_delete',
            'content': {
                'user': user,
                'time': time.strftime('%d %b %Y %X %Z'),
                'prev': prev.strftime('%d %b %Y %X %Z'),
                'message': message,
                'piece': piece
            }
        }))

    async def game_move(self, event):
        move = event['move']
        user = event['user']
        prev = event['prev']
        time = event['time']

        await self.send(text_data=json.dumps({
            'type': 'move',
            'content': {
                'user': user,
                'time': time.strftime('%d %b %Y %X %Z'),
                'prev': prev.strftime('%d %b %Y %X %Z'),
                'piece': move['piece'],
                'from': move['from'],
                'to': move['to']
            }
        }))

    async def kick_user(self, event):
        reason = event['reason']
        user = event['user']
        kickee = event['kickee']
        time = event['time']

        await self.send(text_data=json.dumps({
            'type': 'kick',
            'content': {
                'user': user,
                'kickee': kickee,
                'time': time.strftime('%d %b %Y %X %Z'),
                'reason': reason
            }
        }))
        if self.scope['user'].username == kickee:
            await self.close()