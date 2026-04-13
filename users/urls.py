from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    path("login", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("register", views.RegisterViewClass.as_view(), name="register"),
    path("refresh-token", TokenRefreshView.as_view(), name="token_refresh"),
]
