from rest_framework import serializers
from .models import Lobby, LobbyMembership, Match, MatchPlayer, MatchGame


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


class MatchGameSerializer(serializers.Serializer):
    word_index = serializers.IntegerField()
    is_active = serializers.BooleanField()
    game_id = serializers.IntegerField()
    tries = serializers.SerializerMethodField()
    tries_left = serializers.SerializerMethodField()

    def get_tries(self, obj):
        from game.models import Game

        game = Game.objects.filter(id=obj.game_id).first()
        if game:
            return game.get_tries()
        return []

    def get_tries_left(self, obj):
        from game.models import Game

        game = Game.objects.filter(id=obj.game_id).first()
        if game:
            return game.get_tries_left()
        return 0


class MatchPlayerSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='player.id', read_only=True)
    username = serializers.CharField(source="player.username", read_only=True)
    current_game = serializers.SerializerMethodField()

    class Meta:
        model = MatchPlayer
        fields = ["id", "username", "lives", "current_word_index", "current_game"]

    def get_current_game(self, obj):
        match_game = MatchGame.objects.filter(
            match=obj.match, player=obj.player, word_index=obj.current_word_index
        ).first()
        if match_game:
            return MatchGameSerializer(match_game).data
        return None


class MatchSerializer(serializers.ModelSerializer):
    players = serializers.SerializerMethodField()
    winner = serializers.CharField(
        source="winner.username", read_only=True, allow_null=True
    )

    class Meta:
        model = Match
        fields = ["id", "players", "status", "winner", "lives_per_player", "created_at"]

    def get_players(self, obj):
        match_players = obj.match_players.select_related("player").all()
        return MatchPlayerSerializer(match_players, many=True).data
