from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import DeviceToken


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_device_token(request):
    token = request.data.get("token")

    if not token:
        return Response({"error": "Token required"}, status=400)

    # Prevent duplicate tokens for different users
    DeviceToken.objects.filter(token=token).exclude(user=request.user).delete()

    DeviceToken.objects.get_or_create(
        user=request.user,
        token=token
    )

    return Response({"message": "Device registered successfully"})