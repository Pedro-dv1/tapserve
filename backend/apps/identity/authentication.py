import time
from dataclasses import dataclass

from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication

from .models import Staff
from .permissions import ELEVATED_PERMISSIONS, MANAGEMENT_ROLES


@dataclass(frozen=True)
class StaffIdentity:
    staff: Staff
    strong: bool
    permissions: frozenset[str]

    def allows(self, code: str) -> bool:
        return code in self.permissions and (
            code not in ELEVATED_PERMISSIONS
            or self.strong
            and self.staff.role.name in MANAGEMENT_ROLES
        )


class StaffSessionAuthentication(BaseAuthentication):
    def authenticate(self, request):
        identity = resolve_staff(request.session, request._request.user, touch=True)
        return (
            (identity.staff.user if identity.strong else AnonymousUser(), identity)
            if identity
            else None
        )

    def authenticate_header(self, request):
        return "Session"


def resolve_staff(session, user, *, touch=False):
    identifier = session.get("tapserve_staff_id")
    if not isinstance(identifier, str):
        return None
    now = int(time.time())
    issued = session.get("tapserve_issued_at", 0)
    seen = session.get("tapserve_seen_at", 0)
    if (
        type(issued) is not int
        or type(seen) is not int
        or now - issued > 28800
        or now - seen > 1800
    ):
        session.flush()
        return None
    staff = (
        Staff.objects.select_related("unit__company", "role", "user")
        .filter(id=identifier, active=True, unit__active=True, unit__company__active=True)
        .first()
    )
    if (
        staff is None
        or session.get("tapserve_credential_version") != staff.credential_version
        or (staff.user is not None and not staff.user.is_active)
    ):
        session.flush()
        return None
    strong = session.get("tapserve_auth_strength") == "password"
    if strong and (staff.user_id is None or user.pk != staff.user_id or not user.is_authenticated):
        session.flush()
        return None
    if touch:
        session["tapserve_seen_at"] = now
    return StaffIdentity(staff, strong, frozenset(staff.permissions.values_list("code", flat=True)))
