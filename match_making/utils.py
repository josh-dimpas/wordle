from django.db.models import F
from websocket.services import WebSocketService

from .models import MatchPlayer, MatchGame


def complete_match(match, winner=None):
    match.status = "completed"
    if winner:
        match.winner = winner
    match.save()

    for mp in MatchPlayer.objects.filter(match=match):
        mp.player.matches_count = F("matches_count") + 1
        mp.player.save()

    if winner:
        winner_entry = MatchPlayer.objects.filter(match=match, player=winner).first()
        if winner_entry:
            winner_entry.player.wins = F("wins") + 1
            winner_entry.player.save()


def advance_word(match_player, match, player):
    match_player.current_word_index = F("current_word_index") + 1
    match_player.save()
    match_player.refresh_from_db()

    next_game = MatchGame.objects.filter(
        match=match,
        player=player,
        word_index=match_player.current_word_index,
    ).first()

    if next_game:
        next_game.is_active = True
        next_game.save()

    return match_player


def broadcast_guess_result(match, username, guess, correct, **extra):
    WebSocketService.broadcast_to_match(
        match.id,
        "game:guess_result",
        {"username": username, "guess": guess, "correct": correct, **extra},
    )
