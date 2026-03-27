from django.urls import path

from . import views

urlpatterns = [
    path("login", views.LoginViewClass.as_view(), name="login") ,
    path("register", views.RegisterViewClass.as_view(), name="register") ,
    # This url is purely for testing
    path("jwt/<str:username>", views.JWTViewClass.as_view(), name="jwt-test")
]
