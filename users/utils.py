from django.apps import apps

from .apps import UsersConfig

config: UsersConfig = apps.get_app_config("users")  # type: ignore
