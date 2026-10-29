from __future__ import annotations

from collections.abc import Mapping

from rest_framework import serializers

from .models import Permission, Role, Staff
from .permissions import PERMISSION_CODES


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, Mapping) or set(data) - set(self.fields):
            raise serializers.ValidationError({"non_field_errors": ["Campos não permitidos."]})
        return super().to_internal_value(data)


class PinLoginInput(StrictSerializer):
    company = serializers.SlugField(max_length=80)
    unit = serializers.SlugField(max_length=80)
    login_code = serializers.RegexField(r"^[A-Za-z0-9_-]{1,32}$")
    pin = serializers.RegexField(r"^[0-9]{6,12}$", write_only=True)


class ListQuery(StrictSerializer):
    page = serializers.IntegerField(min_value=1, max_value=1000, default=1)
    search = serializers.CharField(max_length=100, allow_blank=True, default="")
    active = serializers.ChoiceField(choices=["true", "false"], required=False)


class UnitSelectionInput(StrictSerializer):
    membership_id = serializers.UUIDField()


class UnitMembershipOutput(serializers.ModelSerializer):
    unit_id = serializers.UUIDField(read_only=True)
    unit_name = serializers.CharField(source="unit.name")

    class Meta:
        model = Staff
        fields = ["id", "name", "unit_id", "unit_name"]


class PasswordLoginInput(StrictSerializer):
    company = serializers.SlugField(max_length=80)
    unit = serializers.SlugField(max_length=80)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=256, trim_whitespace=False, write_only=True)


class StaffInput(StrictSerializer):
    idempotency_key = serializers.UUIDField(required=False)
    name = serializers.CharField(max_length=100)
    login_code = serializers.RegexField(r"^[A-Za-z0-9_-]{1,32}$")
    pin = serializers.RegexField(r"^[0-9]{6,12}$", write_only=True)
    role_id = serializers.UUIDField()
    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=PERMISSION_CODES), max_length=len(PERMISSION_CODES)
    )

    def validate_permissions(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Permissões duplicadas.")
        return value


class StaffUpdateInput(StrictSerializer):
    name = serializers.CharField(max_length=100, required=False)
    active = serializers.BooleanField(required=False)
    pin = serializers.RegexField(r"^[0-9]{6,12}$", write_only=True, required=False)
    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=PERMISSION_CODES),
        max_length=len(PERMISSION_CODES),
        required=False,
    )
    reason = serializers.CharField(max_length=300, allow_blank=True, default="")

    def validate(self, data):
        if len(data) == 1:
            raise serializers.ValidationError("Nenhuma alteração informada.")
        return data


class StaffOutput(serializers.ModelSerializer):
    role = serializers.CharField(source="role.name")
    permissions: serializers.SlugRelatedField[Permission] = serializers.SlugRelatedField(
        slug_field="code", read_only=True, many=True
    )

    class Meta:
        model = Staff
        fields = ["id", "name", "login_code", "role", "active", "permissions"]
        read_only_fields = fields


class ContextOutput(serializers.Serializer):
    staff = StaffOutput()
    company_name = serializers.CharField()
    unit_id = serializers.UUIDField()
    unit_name = serializers.CharField()
    auth_strength = serializers.ChoiceField(choices=["pin", "password"])


class RoleOutput(serializers.ModelSerializer):
    permissions: serializers.SlugRelatedField[Permission] = serializers.SlugRelatedField(
        source="suggested_permissions", slug_field="code", read_only=True, many=True
    )

    class Meta:
        model = Role
        fields = ["id", "name", "permissions"]
