from django.apps import apps

from game.apps import GameConfig

config: GameConfig = apps.get_app_config('game') # type: ignore
