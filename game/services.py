import random
from typing import Final, List
from django.apps import apps
import requests

from game.apps import GameConfig

config: GameConfig = apps.get_app_config('game')
API_URL: Final = "https://random-word-api.herokuapp.com/word"

class WordService:
    FALLBACK_WORDS = [
        "apple", "orange", "house", "neovim"
    ]

    @classmethod
    def fetch_word(cls) -> str:
        min_length = config.WORD_MIN_LENGTH
        max_length = config.WORD_MAX_LENGTH
        length = random.randint(min_length, max_length)
        
        # Do not catch the error as get_random_word will handle that
        response = requests.get(f"{API_URL}?length={length}")

        if response.status_code == 200:
            data : List[str] = response.json()
            return data[0]
        else:
            raise Exception(f"Random word fetch failed: [{response.status_code}]")

    @classmethod
    def get_random_word(cls) -> str:
        # Try requesting on api
        try:
            return cls.fetch_word()
        except BaseException as e:
            print(f"Error on fetching words: {e}")
            return random.choice(cls.FALLBACK_WORDS)