from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

#need to make peer to peer chat that can be deleted if either user is if security is necessary

class ChatRoom(models.Model):
    name = models.CharField(max_length=200, primary_key=True)
    public = models.BooleanField(default=False)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='adminrooms')
    whitelist = models.ManyToManyField(User, related_name='chatrooms')

    def __str__(self):
        return self.name + ' - ' + self.admin.username

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    username = models.CharField(max_length=200)
    time = models.DateTimeField(default=timezone.now)
    content = models.TextField()

    def __str__(self):
        return self.username + ' - ' + self.time.strftime('%d %b %X')