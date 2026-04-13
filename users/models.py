from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.


class Account(AbstractUser):
    # Test
    wins = models.IntegerField(
        default=0
    )  # For faster querying + wins are stored even if games are deleted
    matches_count = models.IntegerField(default=0)  # ^

    class Meta:
        verbose_name = "account"
        verbose_name_plural = "accounts"

    def __str__(self):
        return self.username
