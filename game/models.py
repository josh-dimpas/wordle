from django.utils import timezone
from typing import List
from django.db import models

from game.apps import config

class Game(models.Model):
    code = models.CharField(max_length=config.GAME_CODE_LENGTH, default='')
    is_win = models.BooleanField(default=False)
    player = models.CharField(default=config.ANON_USERNAME)
    word = models.CharField(max_length=config.WORD_MAX_LENGTH)
    tries = models.JSONField(default=list)
    max_tries = models.IntegerField(default=config.GAME_MAX_TRIES)
    created_at = models.DateTimeField("Created At", default=timezone.now)

    # Type hint the tries
    def get_tries(self) -> List[str]:
        # Loop through the tries, print each character with 1 extra char
        return [self.assess_guess(t) for t in self.tries]
    
    def get_is_finished(self) -> bool:
        tries_left = self.get_tries_left()
        return tries_left == 0 or self.is_win

    def guess(self, input: str):
        self.tries.append(input)

        if input == self.word:
            self.is_win = True

        self.save()

    def assess_guess(self, guess: str) -> str: 
        word = self.word
        exact_sign = config.WORD_CORRECT_EXACT_IDENTIFIER
        partial_sign = config.WORD_CORRECT_PARTIAL_IDENTIFIER

        print(word, guess)

        return ''.join([
            f"{c}{exact_sign if c == word[i] else partial_sign if c in word else ' '}" for i, c in enumerate(guess)
        ])

    def get_tries_left(self) -> int:
        return self.max_tries - len(self.tries)

    def to_json(self):
        tries_left = self.get_tries_left()
        return {
            "tries_left": tries_left,
            "tries": self.get_tries(),
            "word_length": len(self.word),
            "created_at": self.created_at.__str__(),
            **({ "word": self.word } if self.get_is_finished() else {})
        }

    def __str__(self):
        tries = self.get_tries()

        # Join the mapped tries and add the 'tries' left
        tries = "\n".join(tries)

        return f"[{self.word}]\n{tries}\n\nTries Left:{self.get_tries_left()}"
