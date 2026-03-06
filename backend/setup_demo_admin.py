from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.http import JsonResponse

def setup_demo_admin(request):
    """
    TEMPORARY endpoint:
    1️⃣ Runs all migrations
    2️⃣ Creates a demo admin user
    """

    User = get_user_model()

    try:
        # Step 1: run migrations
        call_command("migrate", interactive=False)

        # Step 2: create admin user
        username = "demo_landlady"
        password = "Demo@12345"
        email = "demo@example.com"

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            created = True
        else:
            created = False

        return JsonResponse({
            "status": "success",
            "message": "Migrations applied",
            "admin_created": created,
            "username": username,
            "password": password
        })

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})