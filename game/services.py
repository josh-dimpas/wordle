import random
from typing import Final, List
import requests

from .utils import config

API_URL: Final = "https://random-word-api.herokuapp.com/word"
REQUEST_TIMEOUT: Final = 30


class WordService:
    FALLBACK_WORDS = [
        "apple", "orange", "house", "neovim"
    ]

    @classmethod
    def fetch_word(cls) -> str:
        min_length = config.WORD_MIN_LENGTH
        max_length = config.WORD_MAX_LENGTH
        length = random.randint(min_length, max_length)

        response = requests.get(f"{API_URL}?length={length}", timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            data : List[str] = response.json()
            return data[0]
        else:
            raise Exception(f"Random word fetch failed: [{response.status_code}]")

    @classmethod
    def fetch_words(cls, amount: int) -> List[str]:
        min_length = config.WORD_MIN_LENGTH
        max_length = config.WORD_MAX_LENGTH
        length = random.randint(min_length, max_length)

        response = requests.get(
            f"{API_URL}?length={length}&number={amount}", timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            data : List[str] = response.json()
            return data
        else:
            raise Exception(f"Random word fetch failed: [{response.status_code}]")

    @classmethod
    def get_random_word(cls) -> str:
        # Try requesting on api
        try:
            return cls.fetch_word()
        except requests.exceptions.Timeout:
            print(f"Timeout fetching word, using fallback")
            return random.choice(cls.FALLBACK_WORDS)
        except BaseException as e:
            print(f"Error on fetching words: {e}")
            return random.choice(cls.FALLBACK_WORDS)

    @classmethod
    def get_random_words(cls, amount: int) -> List[str]:
        # Try requesting on api
        try:
            return cls.fetch_words(amount=amount)
        except requests.exceptions.Timeout:
            print(f"Timeout fetching words, using fallback")
            return random.choices(cls.FALLBACK_WORDS, k=amount)
        except BaseException as e:
            print(f"Error on fetching words: {e}")
            return random.choices(cls.FALLBACK_WORDS, k=amount)
