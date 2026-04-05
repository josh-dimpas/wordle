from django.urls import path

from . import views

urlpatterns = [
    path("lobby/create", views.LobbyCreateView.as_view(), name="lobby_create"),
    path("lobby/join", views.LobbyJoinView.as_view(), name="lobby_join"),
    path("lobby/leave", views.LobbyLeaveView.as_view(), name="lobby_leave"),
    path("lobby/current", views.LobbyCurrentView.as_view(), name="lobby_current"),
    path("lobby/ready", views.LobbyReadyView.as_view(), name="lobby_ready"),
    path("lobby/start", views.LobbyStartView.as_view(), name="lobby_start"),
]
