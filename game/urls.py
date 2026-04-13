from django.urls import path

from . import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("leaderboards", views.LeaderboardsView.as_view(), name="leaderboards"),
    path("stats", views.AccountStatsView.as_view(), name="account_stats"),
    path("play", views.PlayView.as_view(), name="play"),
    path("game/<int:game_id>", views.ViewGameView.as_view(), name="view_game"),
    path("game/<int:game_id>/<str:input>", views.GuessView.as_view(), name="guess"),
]
