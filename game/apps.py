from django.apps import AppConfig
from typing import Final

class GameConfig(AppConfig):
    name = 'game'

    ENABLE_AUTH = Final = True

    GAME_CODE_LENGTH: Final = 6
    GAME_MAX_TRIES: Final = 6

    WORD_MAX_LENGTH: Final = 8
    WORD_MIN_LENGTH: Final = 5
    WORD_CORRECT_EXACT_IDENTIFIER: Final = '/'
    WORD_CORRECT_PARTIAL_IDENTIFIER: Final = '+'

    ANON_USERNAME: Final = 'anon'

