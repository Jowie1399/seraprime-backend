from rest_framework import serializers
from .models import DeviceToken


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = "__all__"
        read_only_fields = ("user",)