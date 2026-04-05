import json

from django.views import View

# ? Should create a subclass right? for long term
from django.apps import apps
from django.http import HttpRequest, JsonResponse

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


from users.apps import UsersConfig
from users.models import Account
from users.utils import decode_jwt, encode_jwt

config: UsersConfig = apps.get_app_config('users')

# Create your views here.
@method_decorator(csrf_exempt, name='dispatch')
class LoginViewClass(View):
    def post(self, request: HttpRequest):
        try:
            data = json.loads(request.body)

            username = data.get('username')
            password = data.get('password')

            # Find if user exists with username
            user = Account.objects.filter(username=username).first()

            # ? Should the error message for both username and password the same for security reasons
            if user is None:
                return JsonResponse({ "error": f"User '{username}' does not exist" }, status=401)

            correct_password = user.check_password(password)

            if not correct_password:
                return JsonResponse({ "error": "Invalid credentials"}, status=401)

            # If successful, create a jwt token for username and set expire time
            jwt_encoded = encode_jwt(username)
        
            return JsonResponse({ "token": jwt_encoded, "expires_in": config.JWT_LIFETIME })
        except json.JSONDecodeError as  e:
            print(e)
            return JsonResponse({ "error": "Invalid JSON"}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class RegisterViewClass(View):
    def post(self, request: HttpRequest):
        try:
            data = json.loads(request.body)

            username = data.get('username')
            password = data.get('password') # No hashing needed

            # Check if existing users already have this email
            is_used_username = Account.objects.filter(username=username).exists()

            if is_used_username:
                return JsonResponse({ "error": "Username is already used. Please choose something else" }, status=409)

            # Create a user object using django built in 
            user = Account.objects.create_user(username, 'no-email', password)
            user.save()

            return JsonResponse({ "message": f"User {username} created successfully"}, status=201, safe=False)
        except json.JSONDecodeError as e:
            print(e)
            return JsonResponse({ "error": f"Invalid request body" }, status=403)

@method_decorator(csrf_exempt, name='dispatch')
class JWTViewClass(View):
    def get(self, request: HttpRequest, username:str):
        return JsonResponse({ "token": encode_jwt(username) })

    def post(self, request: HttpRequest, username: str):
        try:
            auth_header = request.headers.get('Authorization')
            token = auth_header[7:] # "Bearer "

            print(token, username)

            token_username, expired = decode_jwt(token)

            return JsonResponse({ "username": token_username, "expired": expired, "valid": token_username == username })
        except json.JSONDecodeError as e:
            print(e)
            return JsonResponse({ "error": "Invalid request body"}, status=403)