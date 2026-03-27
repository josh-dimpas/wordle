from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("leaderboards", views.leaderboards, name="leaderboards"),
    path("<str:username>", views.account_stats, name="view account"),
    path("<str:username>/play", views.play, name="play"),
    path("<str:username>/<str:game_code>", views.view_game, name="view game"),
    path("<str:username>/<str:game_code>/<str:input>", views.guess, name="guess"),
]
