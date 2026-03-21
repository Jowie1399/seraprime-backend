from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, status

from django.utils.dateparse import parse_date

from .models import DeviceToken, Notification
from .serializers import NotificationSerializer


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_device_token(request):
    token = request.data.get("token")
    platform = request.data.get("platform", "")
    device_name = request.data.get("device_name", "")

    if not token:
        return Response({"error": "Token required"}, status=status.HTTP_400_BAD_REQUEST)

    device_token, created = DeviceToken.objects.update_or_create(
        token=token,
        defaults={
            "user": request.user,
            "platform": platform,
            "device_name": device_name,
        },
    )

    return Response(
        {
            "message": "Device registered",
            "created": created,
            "token_id": device_token.id,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unregister_device_token(request):
    token = request.data.get("token")

    if not token:
        return Response({"error": "Token required"}, status=status.HTTP_400_BAD_REQUEST)

    deleted_count, _ = DeviceToken.objects.filter(
        user=request.user,
        token=token,
    ).delete()

    return Response(
        {
            "message": "Device token removed",
            "deleted_count": deleted_count,
        },
        status=status.HTTP_200_OK,
    )


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Notification.objects.filter(user=user).order_by("-created_at")

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        read = self.request.query_params.get("read")

        if start_date:
            parsed_start = parse_date(start_date)
            if parsed_start:
                qs = qs.filter(created_at__date__gte=parsed_start)

        if end_date:
            parsed_end = parse_date(end_date)
            if parsed_end:
                qs = qs.filter(created_at__date__lte=parsed_end)

        if read is not None:
            if read.lower() == "true":
                qs = qs.filter(read=True)
            elif read.lower() == "false":
                qs = qs.filter(read=False)

        return qs

    @action(detail=True, methods=["patch"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.read:
            notification.read = True
            notification.save(update_fields=["read"])
        return Response({"message": "Marked as read"})

    @action(detail=False, methods=["patch"])
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(read=False).update(read=True)
        return Response({
            "message": "All notifications marked as read",
            "updated_count": updated
        })

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = self.get_queryset().filter(read=False).count()
        return Response({"unread_count": count})