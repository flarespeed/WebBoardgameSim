from django.contrib import admin
from .models import GameRoom, BoardTemplate, Move, GameMessage

admin.site.register(GameRoom)
admin.site.register(BoardTemplate)
admin.site.register(Move)
admin.site.register(GameMessage)
