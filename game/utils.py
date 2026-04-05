from typing import Optional

from django.apps import apps
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from django.http import HttpRequest
from game.apps import GameConfig
from users.models import Account

config: GameConfig = apps.get_app_config('game')

def get_user_from_request(request: HttpRequest) -> Optional[int]:
    if not hasattr(request, "META"):
        return None

    # Check for anon
    path_username = getattr(request, "path_username", None)
    if path_username == config.ANON_USERNAME:
        return None

    # Decode JWT
    auth_header = request.META.get('HTTP_AUTHORIZATION', "")
    if not auth_header.startswith("Bearer "):
        return None
        
    token = auth_header[7:]

    try:
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        account = Account.objects.get(id=user_id)
        return account.username
    except (InvalidToken, TokenError, Account.DoesNotExist) as e:
        return None