from django.shortcuts import render, reverse, redirect, get_object_or_404
from .models import GameRoom, BoardTemplate, Move, GameMessage
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.core.validators import slug_re
import json

@login_required
def index(request):
    user = request.user
    admingames = user.admingames.order_by('last_update')
    gamerooms = user.gamerooms.order_by('last_update').exclude(admin=user)
    templates = BoardTemplate.objects.filter(visible=True)
    context = {
        'admingames': admingames, 'gamerooms': gamerooms, 'templates': templates
    }
    return render(request, 'tabletops/index.html', context)

@login_required
def create_room(request):
    parsed = json.loads(request.body)
    if not parsed['room_name']:
        return JsonResponse({'error': 'Please fill out room name'})
    if not slug_re.match(parsed['room_name']):
        return JsonResponse({'error': 'Please input a room name that is url safe(no spaces or special characters)'})
    if not parsed['template']:
        return JsonResponse({'error': 'Please pick a template'})
    room_name = parsed['room_name']
    if GameRoom.objects.filter(name=room_name).exists():
        return JsonResponse({'error': 'A room with that name already exists.'})
    template = BoardTemplate.objects.filter(name=parsed['template'])
    if template.exists():
        new = GameRoom(name=room_name, admin=request.user, base_template=template[0], board_state=template[0].board_state, board_width=template[0].board_width, board_height=template[0].board_height)
        new.save()
        new.whitelist.add(request.user)
        resp = {'redirect': reverse('tabletops:room', args=(new.name,))}
        return JsonResponse(resp)
    return JsonResponse({'error': 'Template with that name does not exist.'})

@login_required
def room(request, room_name):
    current_room = GameRoom.objects.filter(name=room_name)
    if current_room:
        if current_room[0].whitelist.filter(id=request.user.id).exists() or current_room[0].admin == request.user:
            return render(request, 'tabletops/board.html', {
            'room_name': current_room[0].name, 'board': current_room[0].board_state, 'board_width': current_room[0].board_width, 'board_height': current_room[0].board_height, 'calcVh': 97/current_room[0].board_height, 'off_board': current_room[0].off_board, 'admin': current_room[0].admin == request.user,
            })
    return redirect(reverse('tabletops:index'))

@staff_member_required
def template_admin(request):
    templates = BoardTemplate.objects.all()
    return render(request, 'tabletops/templateadmin.html', {
        'templates': templates
    })

@staff_member_required
def create(request):
    name = request.POST['name']
    height = int(request.POST['height'])
    width = int(request.POST['width'])
    board_state = '['
    for i in range(height*width):
        board_state += "{'color': 'white', 'pieces': [], 'x': " + str(i%width) + ", 'y': " + str((i//width) + 1) + "},"
    board_state += ']'
    new = BoardTemplate(name=name, board_state=board_state, board_width=width, board_height=height)
    new.save()
    return redirect(reverse('tabletops:template_edit', args=(new.name,)))

@staff_member_required
def template_edit(request, template_name):
    template = get_object_or_404(BoardTemplate, pk=template_name)
    return render(request, 'tabletops/template.html', {
        'board_state': template.board_state, 'board_width': template.board_width, 'board_height': template.board_height, 'template_name': template_name, 'visible': template.visible
    })

@staff_member_required
def save_template(request):
    parsed = json.loads(request.body)
    template = get_object_or_404(BoardTemplate, pk=parsed['template_name'])
    print(parsed)
    template.board_state = parsed['board_state']
    template.visible = parsed['visible']
    template.save()
    return HttpResponse('saved successfully')

@login_required
def history(request):
    data = json.loads(request.body)
    room = get_object_or_404(GameRoom, name=data['room_name'])
    whitelist = room.whitelist.all()
    if request.user in whitelist:
        history = []
        message_list = GameMessage.objects.all()
        for message in message_list:
            history.append(message)
        move_list = Move.objects.all()
        for move in move_list:
            history.append(move)
        history.sort(key=lambda moment: moment.time, reverse=True)
        hist_for_json = []
        for item in history:
            if item.__class__.__name__ == 'GameMessage':
                hist_for_json.append({'username': item.username, 'time': item.time.strftime('%d %b %Y %X %Z'), 'content': item.content})
            elif item.__class__.__name__ == 'Move':
                parsed = json.loads(item.content)
                print(parsed)
                if parsed['from']:
                    if 'pieceName' in parsed:
                        if parsed['from']['i'] == -1:
                            constructed_message = 'moved ' + parsed['pieceName'] + ' from off board to x: ' + str(parsed['to']['x']) + ', y: ' + str(parsed['to']['y']) + '.'
                        elif parsed['to']['i'] == -1:
                            constructed_message = 'moved ' + parsed['pieceName'] + ' from x: ' + str(parsed['from']['x']) + ', y: ' + str(parsed['from']['y']) + ' off of board.'
                        else:
                            constructed_message = 'moved ' + parsed['pieceName'] + ' from x: ' + str(parsed['from']['x']) + ', y: ' + str(parsed['from']['y']) + ' to x: ' + str(parsed['to']['x']) + ', y: ' + str(parsed['to']['y']) + '.'
                    else:
                        if parsed['from']['i'] == -1:
                            constructed_message = 'moved unknown piece from off board to x: ' + str(parsed['to']['x']) + ', y: ' + str(parsed['to']['y']) + '.'
                        elif parsed['to']['i'] == -1:
                            constructed_message = 'moved unknown piece from x: ' + str(parsed['from']['x']) + ', y: ' + str(parsed['from']['y']) + ' off of board.'
                        else:
                            constructed_message = 'moved unknown piece from x: ' + str(parsed['from']['x']) + ', y: ' + str(parsed['from']['y']) + ' to x: ' + str(parsed['to']['x']) + ', y: ' + str(parsed['to']['y']) + '.'
                hist_for_json.append({'username': 'system', 'time': item.time.strftime('%d %b %Y %X %Z'), 'content': item.username + constructed_message})
        return JsonResponse({'content': hist_for_json, 'error': ''})
    return JsonResponse({'content': [], 'error': "You ain't on the list"})

@login_required
def whitelist(request):
    data = json.loads(request.body)
    room = get_object_or_404(GameRoom, name=data['room_name'])
    whitelist = room.whitelist.all()
    username_list = []
    if request.user in whitelist:
        for user in whitelist:
            username_list.append(user.username)
    if request.user == room.admin:
        if data['action'] != 'invite':
            return JsonResponse({'whitelist': username_list, 'error': '', 'admin': True})
        found = User.objects.filter(username=data['username'])
        if found.exists():
            invitee = found[0]
            room.whitelist.add(invitee)
            username_list.append(invitee.username)
            return JsonResponse({'whitelist': username_list, 'error': '', 'admin': True})
        else:
            return JsonResponse({'whitelist': username_list, 'error': 'No user by that name found', 'admin': True})
    else:
        if data['action'] != 'invite':
            return JsonResponse({'whitelist': username_list, 'error': '', 'admin': False})
        else:
            return JsonResponse({'whitelist': username_list, 'error': 'non admins are not allowed to invite other players, nice try though', 'admin': False})
