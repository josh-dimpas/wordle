
from functools import wraps
from django.apps import apps
from django.http import HttpRequest, JsonResponse
from game.apps import GameConfig
from users.utils import decode_jwt

config: GameConfig = apps.get_app_config('game')

class AccountAccessMiddleware:
    def __init__(self, match_username: bool = False):
        self.match_username = match_username

    def __call__(self, view_func):
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            path_username = kwargs['username']

            # Skip authorizing if path username is anon
            if path_username == config.ANON_USERNAME:
                return view_func(request, *args, **kwargs)
            
            auth_header = request.headers.get('Authorization')

            if auth_header is None:
                return JsonResponse({ "error": "Missing JWT Token"}, status=401)

            token = auth_header[7:]

            username, expired = decode_jwt(token)


            if self.match_username and path_username != username:
                return JsonResponse({ "error": "JWT and path username mismatch"}, status=401)

            if expired:
                return JsonResponse({ "error": "Expired JWT Token"}, status=401)

            return view_func(request, *args, **kwargs)
        return wrapper