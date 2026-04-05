from django.conf import settings
from django.contrib.auth.models import User
from jwt import ( JWT)

import random
import string

from django.http import HttpRequest
from game.apps import GameConfig
from users.models import Account

config: GameConfig = apps.get_app_config('game')

def generate_code():
    characters = string.ascii_letters + string.digits

    # Continuously create code until a unique one appears 
    while True:
        code = random.choice(string.ascii_letters) + "".join(random.choices(characters, k=config.GAME_CODE_LENGTH))
        if not Game.objects.filter(code=code).exists():
            return code

def get_user(request: HttpRequest):
    auth_header = request.headers.get('Authorization', '')

    # For Anon
    if request.path.startswith(f'/{config.ANON_USERNAME}'):
        return None

    token = auth_header[7:]

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return User.objects.get(username=payload['username'])
    except BaseException as e:
        print(e)
        pass