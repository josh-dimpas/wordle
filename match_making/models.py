from django.db import models
from django.utils import timezone

from django.apps import apps
from users.models import Account

config = apps.get_app_config("game")


class Lobby(models.Model):
    code = models.CharField(max_length=9, unique=True)
    owner = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="owned_lobbies"
    )
    players = models.ManyToManyField(
        Account, through="LobbyMembership", related_name="lobbies"
    )
    has_started = models.BooleanField(default=False)
    created_at = models.DateTimeField("Created At", default=timezone.now)

    def invalidate(self):
        self.delete()

    def remove_player(self, player: Account):
        membership = self.memberships.filter(player=player).first()
        if membership:
            membership.delete()

        self.refresh_from_db()

        if self.players.count() == 0:
            self.invalidate()
        elif self.owner == player:
            new_owner = self.players.first()
            if new_owner:
                self.owner = new_owner
                self.save()

    def __str__(self):
        return f"Lobby {self.code}"


class LobbyMembership(models.Model):
    lobby = models.ForeignKey(
        Lobby, on_delete=models.CASCADE, related_name="memberships"
    )
    player = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="lobby_memberships"
    )
    is_ready = models.BooleanField(default=False)
    joined_at = models.DateTimeField("Joined At", default=timezone.now)

    class Meta:
        unique_together = ("lobby", "player")


class Match(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("completed", "Completed"),
    ]

    lobby = models.ForeignKey(
        Lobby, on_delete=models.CASCADE, related_name="matches", null=True, blank=True
    )
    players = models.ManyToManyField(Account, related_name="matches")
    lives_per_player = models.IntegerField(default=config.MULTIPLAYER_LIVES)
    winner = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_matches",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField("Created At", default=timezone.now)

    def __str__(self):
        return f"Match {self.id} - {self.status}"


class MatchPlayer(models.Model):
    match = models.ForeignKey(
        Match, on_delete=models.CASCADE, related_name="match_players"
    )
    player = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="match_entries"
    )
    lives = models.IntegerField(default=config.MULTIPLAYER_LIVES)
    current_word_index = models.IntegerField(default=0)
    joined_at = models.DateTimeField("Joined At", default=timezone.now)

    class Meta:
        unique_together = ("match", "player")


class MatchGame(models.Model):
    match = models.ForeignKey(
        Match, on_delete=models.CASCADE, related_name="match_games"
    )
    player = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="match_games"
    )
    word_index = models.IntegerField()
    is_active = models.BooleanField(default=False)
    game_id = models.IntegerField()

    class Meta:
        unique_together = ("match", "player", "word_index")
