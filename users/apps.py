import os
from django.apps import AppConfig, apps


class UsersConfig(AppConfig):
    name = 'users'

    JWT_LIFETIME = int(os.getenv('JWT_LIFETIME_SECONDS', '7200'))
    JWT_KEY = os.getenv('JWT_SECRET')


config: UsersConfig = apps.get_app_config('users')