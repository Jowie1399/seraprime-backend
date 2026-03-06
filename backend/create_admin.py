from django.contrib.auth.models import User
from django.http import JsonResponse
from backend.create_admin import create_admin



def create_admin(request):
    """
    Temporary endpoint to create a Django superuser in production.
    Use once then remove.
    """

    username = "admin"
    password = "admin12345"
    email = "admin@seraprime.com"

    if User.objects.filter(username=username).exists():
        return JsonResponse({
            "status": "exists",
            "message": "Admin user already exists"
        })

    User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )

    return JsonResponse({
        "status": "success",
        "message": "Admin user created",
        "username": username,
        "password": password
    })