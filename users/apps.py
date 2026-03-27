from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'users'

    JWT_LIFETIME = 7200 # 2 hrs
    JWT_KEY = b'pleasedonthackme'
