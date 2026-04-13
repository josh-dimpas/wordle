import random
from typing import Final, List
import requests

from .utils import config

API_URL: Final = "https://random-word-api.herokuapp.com/word"
REQUEST_TIMEOUT: Final = 30


class WordService:
    FALLBACK_WORDS = [
        "small",
        "class",
        "space",
        "built",
        "award",
        "fiber",
        "forth",
        "layer",
        "state",
        "basis",
        "sized",
        "stuck",
        "flash",
        "faith",
        "alone",
        "album",
        "argue",
        "error",
        "might",
        "valid",
        "civil",
        "logic",
        "forum",
        "arise",
        "prove",
        "night",
        "still",
        "later",
        "drive",
        "noise",
        "blind",
        "taxes",
        "newly",
        "stage",
        "match",
        "shirt",
        "today",
        "hotel",
        "needs",
        "quick",
        "chief",
        "harry",
        "anger",
        "hence",
        "fresh",
        "lower",
        "laser",
        "slide",
        "mouth",
        "group",
        "strip",
        "ratio",
        "drink",
        "billy",
        "frame",
        "alike",
        "drama",
        "input",
        "clean",
        "value",
        "badly",
        "japan",
        "crime",
        "crash",
        "henry",
        "stand",
        "happy",
        "watch",
        "great",
        "worst",
        "alert",
        "adopt",
        "power",
        "there",
        "smith",
        "chain",
        "refer",
        "craft",
        "shelf",
        "elite",
        "cream",
        "their",
        "buyer",
        "think",
        "apply",
        "along",
        "chase",
        "brand",
        "sound",
        "place",
        "world",
        "sorry",
        "point",
        "angry",
        "trade",
        "noted",
        "local",
        "steel",
        "drawn",
        "cheap",
    ]

    @classmethod
    def fetch_word(cls) -> str:
        min_length = config.WORD_MIN_LENGTH
        max_length = config.WORD_MAX_LENGTH
        length = random.randint(min_length, max_length)

        response = requests.get(f"{API_URL}?length={length}", timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            data: List[str] = response.json()
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
            data: List[str] = response.json()
            return data
        else:
            raise Exception(f"Random word fetch failed: [{response.status_code}]")

    @classmethod
    def get_random_word(cls) -> str:
        try:
            return cls.fetch_word()
        except requests.exceptions.Timeout:
            print("Timeout fetching word, using fallback")
            return random.choice(cls.FALLBACK_WORDS)
        except BaseException as e:
            print(f"Error on fetching word: {e}")
            return random.choice(cls.FALLBACK_WORDS)

    @classmethod
    def get_random_words(cls, amount: int) -> List[str]:
        try:
            return cls.fetch_words(amount=amount)
        except requests.exceptions.Timeout:
            print("Timeout fetching words, using fallback")
            return random.choices(cls.FALLBACK_WORDS, k=amount)
        except BaseException as e:
            print(f"Error on fetching words: {e}")
            return random.choices(cls.FALLBACK_WORDS, k=amount)
