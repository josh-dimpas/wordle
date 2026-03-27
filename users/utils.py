from django.apps import apps
from jwt import ( JWT, supported_key_types )

from datetime import datetime, timedelta
from users.apps import UsersConfig

jwt = JWT()
config: UsersConfig = apps.get_app_config('users')

def decode_jwt(
    token: str,
    secret: str = config.JWT_KEY
) -> tuple[ str, bool ]: 
    jwt_secret = supported_key_types()['oct'](secret)

    payload = jwt.decode(token, jwt_secret)
    
    username = payload['username']
    expires = payload['expires']

    print(expires, username)

    return username, False

def encode_jwt(
    username: str, 
    lifetime_seconds: int = config.JWT_LIFETIME, 
    secret: str = config.JWT_KEY
) -> str: 
    jwt_secret = supported_key_types()['oct'](secret)

    payload = {
        "username": username,
        "expires": (datetime.now() + timedelta(seconds=lifetime_seconds)).isoformat()
    }

    return jwt.encode(payload, jwt_secret)
