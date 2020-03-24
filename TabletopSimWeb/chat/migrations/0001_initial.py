# Generated by Django 3.0.4 on 2020-03-13 17:16

from django.conf import settings
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=200)),
                ('messageTime', models.DateTimeField(default=django.utils.timezone.now)),
                ('content', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='ChatRoom',
            fields=[
                ('name', models.CharField(max_length=200, primary_key=True, serialize=False)),
                ('public', models.BooleanField(default=False)),
                ('whitelist', models.ManyToManyField(related_name='chatrooms', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]