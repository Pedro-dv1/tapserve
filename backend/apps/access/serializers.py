from rest_framework import serializers

from apps.identity.serializers import StrictSerializer

from .models import DeviceAccess, ServicePoint


class PointInput(StrictSerializer):
    menu = serializers.UUIDField(required=False)
    number = serializers.IntegerField(
        min_value=1, max_value=999999, required=False, allow_null=True
    )
    name = serializers.CharField(max_length=100, allow_blank=True, default="")
    type = serializers.ChoiceField(choices=ServicePoint.Kind.choices)
    nfc_enabled = serializers.BooleanField(default=True)
    qr_enabled = serializers.BooleanField(default=True)
    idempotency_key = serializers.UUIDField()

    def validate(self, data):
        if data["type"] == "TABLE" and not data.get("number"):
            raise serializers.ValidationError({"number": "Informe o número da mesa."})
        if data["type"] != "TABLE" and not data["name"]:
            raise serializers.ValidationError({"name": "Informe o nome do ponto."})
        return data


class PointUpdateInput(StrictSerializer):
    number = serializers.IntegerField(min_value=1, max_value=999999, required=False)
    name = serializers.CharField(max_length=100, allow_blank=True, required=False)
    menu = serializers.UUIDField(required=False)
    active = serializers.BooleanField(required=False)
    access_enabled = serializers.BooleanField(required=False)
    nfc_enabled = serializers.BooleanField(required=False)
    qr_enabled = serializers.BooleanField(required=False)
    block_new_devices = serializers.BooleanField(required=False)
    reason = serializers.CharField(max_length=300, allow_blank=True, default="")

    def validate(self, data):
        if len(data) == 1:
            raise serializers.ValidationError("Nenhuma alteração informada.")
        return data


class ReasonInput(StrictSerializer):
    reason = serializers.CharField(max_length=300, allow_blank=True, default="")


class AccessInput(StrictSerializer):
    public_token = serializers.RegexField(r"^[A-Za-z0-9_-]{43}$", write_only=True)


class PointOutput(serializers.ModelSerializer):
    class Meta:
        model = ServicePoint
        fields = [
            "id",
            "number",
            "name",
            "type",
            "active",
            "access_enabled",
            "token_version",
            "nfc_enabled",
            "qr_enabled",
            "block_new_devices",
            "menu",
        ]


class DeviceOutput(serializers.ModelSerializer):
    class Meta:
        model = DeviceAccess
        fields = ["id", "issued_at", "expires_at", "revoked_at"]


class PublicContextOutput(serializers.Serializer):
    device_id = serializers.UUIDField()
    point = PointOutput()
    company_name = serializers.CharField()
    unit_name = serializers.CharField()
    unit_timezone = serializers.CharField()
    leftover_packaging_enabled = serializers.BooleanField()
    unit_logo_url = serializers.CharField(allow_null=True)
    expires_at = serializers.DateTimeField()


class PointUrlOutput(serializers.Serializer):
    url = serializers.URLField()


class IdentifierInput(ReasonInput):
    action = serializers.ChoiceField(choices=["ROTATE", "ASSOCIATE"])
    expected_version = serializers.IntegerField(min_value=1)
    confirmed = serializers.BooleanField(default=False)
    url = serializers.URLField(max_length=500, required=False)


class PresenceOutput(serializers.Serializer):
    connected_devices = serializers.IntegerField()
    timeout_seconds = serializers.IntegerField()
