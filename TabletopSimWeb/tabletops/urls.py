from django.urls import path

from . import views

app_name = 'tabletops'
urlpatterns = [
    path('', views.index, name='index'),
    path('templateadmin/', views.template_admin, name='template_admin'),
    path('template/<str:template_name>/', views.template_edit, name='template_edit'),
    path('createTemplate/', views.create, name='create'),
    path('newRoom/', views.create_room, name='newroom'),
    path('room/<str:room_name>/', views.room, name='room'),
    path('savetemp/', views.save_template, name='save_temp'),
    path('whitelist/', views.whitelist, name='whitelist')
]