from django.apps import AppConfig, apps
from typing import Final

import os

class GameConfig(AppConfig):
    name = 'game'

    GAME_CODE_LENGTH: Final = int(os.getenv('GAME_CODE_LENGTH', '6'))
    GAME_MAX_TRIES: Final = int(os.getenv('GAME_MAX_TRIES', '6'))

    WORD_MAX_LENGTH: Final = int(os.getenv('WORD_MAX_LENGTH', '5'))
    WORD_MIN_LENGTH: Final = int(os.getenv('WORD_MIN_LENGTH', '5'))
    WORD_CORRECT_EXACT_IDENTIFIER: Final = os.getenv('WORD_CHAR_EXACT_IDENTIFIER', '/')
    WORD_CORRECT_PARTIAL_IDENTIFIER: Final = os.getenv('WORD_CHAR_PARTIAL_IDENTIFIER', '+')

    ANON_USERNAME: Final = os.getenv('ANON_USERNAME', 'anon')

config: GameConfig = apps.get_app_config('game')