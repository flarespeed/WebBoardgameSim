from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class BoardTemplate(models.Model):
    name = models.CharField(max_length=200, primary_key=True)
    board_state = models.TextField()
    board_width = models.IntegerField()
    board_height = models.IntegerField()
    visible = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class GameRoom(models.Model):
    name = models.SlugField(max_length=200, primary_key=True)
    public_spectators = models.BooleanField(default=False)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admingames')
    whitelist = models.ManyToManyField(User, related_name='gamerooms')
    board_state = models.TextField()
    off_board = models.TextField(default='[]')
    board_width = models.IntegerField()
    board_height = models.IntegerField()
    base_template = models.ForeignKey(BoardTemplate, on_delete=models.SET_NULL, related_name='gameInstances', null=True, blank=True)
    last_update = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name + ' - ' + self.admin.username


class Move(models.Model):
    room = models.ForeignKey(GameRoom, on_delete=models.CASCADE, related_name='moves')
    username = models.CharField(max_length=200)
    time = models.DateTimeField(default=timezone.now)
    content = models.TextField()

    def __str__(self):
        return self.username + ' - ' + self.time.strftime('%d %b %X')

class GameMessage(models.Model):
    room = models.ForeignKey(GameRoom, on_delete=models.CASCADE, related_name='GameMessages')
    username = models.CharField(max_length=200)
    time = models.DateTimeField(default=timezone.now)
    content = models.TextField()

    def __str__(self):
        return self.username + ' - ' + self.time.strftime('%d %b %X')