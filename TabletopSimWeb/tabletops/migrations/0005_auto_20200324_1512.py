# Generated by Django 3.0.4 on 2020-03-24 22:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tabletops', '0004_gameroom_off_board'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gameroom',
            name='name',
            field=models.SlugField(max_length=200, primary_key=True, serialize=False),
        ),
    ]
