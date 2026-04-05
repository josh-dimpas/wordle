from django.db import models
from django.utils import timezone

from users.models import Account


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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField("Created At", default=timezone.now)

    def __str__(self):
        return f"Match {self.id} - {self.status}"
