from django.core.management import call_command
from django.http import JsonResponse

def migrate(request):
    try:
        call_command("makemigrations")
        call_command("migrate")
        return JsonResponse({"status": "success", "message": "Migrations applied"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})