from rest_framework import serializers
from .models import Game


class GameSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    player = serializers.CharField(source="player.username", read_only=True)
    tries_left = serializers.SerializerMethodField()
    tries = serializers.SerializerMethodField()
    word_length = serializers.SerializerMethodField()
    word = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    def get_tries_left(self, obj):
        return obj.get_tries_left()

    def get_tries(self, obj):
        return obj.get_tries()

    def get_word_length(self, obj):
        return len(obj.word)

    def get_word(self, obj):
        if obj.get_is_finished():
            return obj.word
        return None


class GameCreateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Game
        fields = ["id"]


class GuessSerializer(serializers.Serializer):
    input = serializers.CharField(max_length=50)


class MatchHistorySerializer(serializers.Serializer):
    game_id = serializers.IntegerField()
    won = serializers.BooleanField()
    opponent = serializers.CharField()
    opponent_id = serializers.IntegerField()
    date = serializers.DateTimeField()


class GameSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    won = serializers.BooleanField(source="is_win")
    tries_left = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    def get_tries_left(self, obj):
        return obj.get_tries_left()


class LeaderboardSerializer(serializers.Serializer):
    username = serializers.CharField()
    wins = serializers.IntegerField()
    matches_count = serializers.IntegerField()
