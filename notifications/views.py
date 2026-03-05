from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets

from django.utils.dateparse import parse_date

from .models import DeviceToken, Notification
from .serializers import DeviceTokenSerializer, NotificationSerializer


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


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        user = self.request.user
        qs = Notification.objects.filter(user=user)

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if start_date:
            qs = qs.filter(created_at__date__gte=parse_date(start_date))

        if end_date:
            qs = qs.filter(created_at__date__lte=parse_date(end_date))

        return qs

    @action(detail=True, methods=["patch"])
    def mark_read(self, request, pk=None):

        notification = self.get_object()
        notification.read = True
        notification.save()

        return Response({"message": "Marked as read"})