from rest_framework.permissions import BasePermission

PERMISSION_CODES = (
    "VIEW_OPERATION",
    "VIEW_ALL_TABLES",
    "CREATE_MANUAL_ORDER",
    "EDIT_ORDER",
    "CANCEL_ORDER",
    "ASSIGN_SERVICE_REQUEST",
    "TRANSFER_SESSION",
    "MERGE_TABLES",
    "SPLIT_TABLES",
    "REGISTER_PAYMENT",
    "CLOSE_SESSION",
    "REOPEN_SESSION",
    "CREATE_DISCOUNT",
    "APPLY_MANUAL_DISCOUNT",
    "MANAGE_MENU",
    "MANAGE_STAFF",
    "MANAGE_SETTINGS",
    "VIEW_REPORTS",
    "VIEW_AUDIT",
    "MANAGE_SERVICE_POINTS",
    "PROVISION_NFC",
    "ROTATE_SERVICE_POINT_TOKEN",
    "LOCK_NFC_TAG",
    "UPDATE_PRODUCTION_STATUS",
    "CLAIM_DELIVERY",
    "COMPLETE_DELIVERY",
)
ROLE_DEFAULTS = {
    "OWNER": PERMISSION_CODES,
    "ADMIN": PERMISSION_CODES,
    "MANAGER": (
        "VIEW_OPERATION",
        "VIEW_ALL_TABLES",
        "CREATE_MANUAL_ORDER",
        "EDIT_ORDER",
        "CANCEL_ORDER",
        "ASSIGN_SERVICE_REQUEST",
        "TRANSFER_SESSION",
        "MERGE_TABLES",
        "SPLIT_TABLES",
        "REGISTER_PAYMENT",
        "CLOSE_SESSION",
        "MANAGE_MENU",
        "MANAGE_SETTINGS",
        "VIEW_REPORTS",
        "VIEW_AUDIT",
        "MANAGE_SERVICE_POINTS",
        "UPDATE_PRODUCTION_STATUS",
        "CLAIM_DELIVERY",
        "COMPLETE_DELIVERY",
    ),
    "CASHIER": ("VIEW_OPERATION", "VIEW_ALL_TABLES", "REGISTER_PAYMENT", "CLOSE_SESSION"),
    "WAITER": (
        "VIEW_OPERATION",
        "VIEW_ALL_TABLES",
        "CREATE_MANUAL_ORDER",
        "ASSIGN_SERVICE_REQUEST",
        "CLAIM_DELIVERY",
        "COMPLETE_DELIVERY",
    ),
    "KITCHEN": ("VIEW_OPERATION", "UPDATE_PRODUCTION_STATUS"),
    "BAR": ("VIEW_OPERATION", "UPDATE_PRODUCTION_STATUS"),
}
ELEVATED_PERMISSIONS = {
    "MANAGE_STAFF",
    "MANAGE_MENU",
    "MANAGE_SETTINGS",
    "VIEW_REPORTS",
    "VIEW_AUDIT",
    "MANAGE_SERVICE_POINTS",
    "PROVISION_NFC",
    "ROTATE_SERVICE_POINT_TOKEN",
    "LOCK_NFC_TAG",
}
MANAGEMENT_ROLES = {"OWNER", "ADMIN", "MANAGER"}


class IsActiveStaff(BasePermission):
    def has_permission(self, request, view):
        return request.auth is not None


class CanManageStaff(IsActiveStaff):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.auth.allows("MANAGE_STAFF")


def require_permission(identity, code: str) -> None:
    from rest_framework.exceptions import PermissionDenied

    from .models import Staff

    current = (
        Staff.objects.filter(
            id=identity.staff.id,
            unit_id=identity.staff.unit_id,
            active=True,
            unit__active=True,
            unit__company__active=True,
            credential_version=identity.staff.credential_version,
            permissions__code=code,
        )
        .exclude(user__is_active=False)
        .exists()
    )
    if not identity.allows(code) or not current:
        raise PermissionDenied()
