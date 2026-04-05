import json

from django.views import View

from django.http import HttpRequest, JsonResponse

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import Account

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
