from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.http import JsonResponse

User = get_user_model()


def reset_demo_admin(request):
    try:

        # Run migrations first
        call_command("migrate")

        username = "admin"
        email = "werejoe94@gmail.com"
        password = "#Seraprime350850%"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
            }
        )

        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()

        return JsonResponse({
            "status": "success",
            "username": username,
            "password": password
        })

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        })