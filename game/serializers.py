from rest_framework import serializers
from .models import Game


class GameSerializer(serializers.ModelSerializer):
    tries_left = serializers.SerializerMethodField()
    word_length = serializers.SerializerMethodField()
    word = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = ["id", "tries_left", "tries", "word_length", "created_at", "word"]
        read_only_fields = [
            "id",
            "tries_left",
            "tries",
            "word_length",
            "created_at",
            "word",
        ]

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


class AccountStatsSerializer(serializers.Serializer):
    games_played = serializers.IntegerField()
    games_won = serializers.IntegerField()
    games = serializers.ListField()


class GameSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    won = serializers.BooleanField()
    tries_left = serializers.IntegerField()
    created_at = serializers.DateTimeField()
