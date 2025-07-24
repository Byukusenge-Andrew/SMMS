from django.urls import path
from . import views

urlpatterns = [
    path("", views.MessageListCreateView.as_view(), name="message-list-create"),
    path("send/", views.send_message_now, name="send-message"),
    path("automated/", views.send_automated_message, name="automated-message"),
]