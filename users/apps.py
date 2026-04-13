import os
from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'users'

    JWT_LIFETIME = int(os.getenv('JWT_LIFETIME_SECONDS', '7200'))
    JWT_KEY = os.getenv('JWT_SECRET', "")

