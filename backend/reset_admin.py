from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.http import JsonResponse

User = get_user_model()

def reset_demo_admin(request):
    try:
        # Run migrations in case they weren't applied
        call_command("makemigrations")
        call_command("migrate")

        # <-- SET THE CORRECT SUPERUSER CREDENTIALS HERE -->
        username = "kinsley_admin"
        email = "werejoe94@gmail.com"
        password = "#Seraprime350850%"

        user, created = User.objects.get_or_create(username=username, defaults={
            "email": email,
            "is_staff": True,
            "is_superuser": True,
        })

        if not created:
            user.email = email
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)  # Important: hashes the password
            user.save()
            updated = True
        else:
            user.set_password(password)
            user.save()
            updated = True

        return JsonResponse({
            "status": "success",
            "admin_created_or_updated": updated,
            "username": username,
            "password": password
        })

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        })