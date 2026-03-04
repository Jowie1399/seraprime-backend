from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import DeviceToken
from .serializers import DeviceTokenSerializer


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_device_token(request):
    token = request.data.get("token")

    if not token:
        return Response({"error": "Token required"}, status=400)

    DeviceToken.objects.update_or_create(
        token=token,
        defaults={"user": request.user}
    )

    return Response({"message": "Device registered"})