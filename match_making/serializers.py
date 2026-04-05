from rest_framework import serializers
from .models import Lobby, LobbyMembership, Match


class LobbyMembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="player.username", read_only=True)

    class Meta:
        model = LobbyMembership
        fields = ["username", "is_ready", "joined_at"]


class LobbySerializer(serializers.ModelSerializer):
    owner = serializers.CharField(source="owner.username", read_only=True)
    players = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Lobby
        fields = [
            "id",
            "code",
            "owner",
            "players",
            "has_started",
            "is_owner",
            "created_at",
        ]

    def get_players(self, obj):
        memberships = obj.memberships.select_related("player").all()
        return LobbyMembershipSerializer(memberships, many=True).data

    def get_is_owner(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.owner == request.user
        return False


class JoinLobbySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=9)


class MatchSerializer(serializers.ModelSerializer):
    players = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = ["id", "players", "status", "created_at"]

    def get_players(self, obj):
        return [player.username for player in obj.players.all()]
