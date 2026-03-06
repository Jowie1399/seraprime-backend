from django.contrib.auth import get_user_model
from django.http import JsonResponse

def reset_admin(request):
    """
    TEMPORARY endpoint to reset superuser credentials.
    """
    User = get_user_model()

    try:
        # Replace these with your new credentials
        username = "kinsley_admin"
        password = "seraprime350850%"
        email = "werejoe94@gmail"

        admin = User.objects.filter(is_superuser=True).first()
        if admin:
            admin.username = username
            admin.email = email
            admin.set_password(password)
            admin.save()
            updated = True
        else:
            updated = False

        return JsonResponse({
            "status": "success",
            "admin_updated": updated,
            "username": username,
            "password": password
        })

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})