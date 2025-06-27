from django.urls import path
from .views import *
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', notification_list, name='list'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('<int:pk>/', views.notification_detail, name='detail'),
    path('unread-count/', views.unread_count, name='unread_count'),



]
