"""One authoritative confirmation transaction creates the first occupation and bill items."""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.access.models import DeviceAccess, ServicePoint
from apps.catalog.models import Product
from apps.catalog.services import point_menu, quote
from apps.identity.models import AuditEvent
from apps.identity.permissions import require_permission
from apps.identity.services import rate_limit
from common.idempotency import Conflict, remember, replay

from .models import (
    OrderBatch,
    OrderItem,
    SelectedOption,
    ServiceRequest,
    ServiceSession,
    SessionParticipant,
    SessionPoint,
)

OPEN_STATES = ("OPEN", "CHECK_REQUESTED", "CLOSING", "REOPENED")


def require_device(device, point):
    device = DeviceAccess.objects.get(id=device.id)
    if (
        device.point_id != point.id
        or device.revoked_at
        or device.expires_at <= timezone.now()
        or device.point_token_version != point.token_version
        or not point.active
        or not point.unit.active
        or not point.unit.company.active
    ):
        raise PermissionDenied()
    return device


def session_data(session):
    return {
        "id": str(session.id),
        "status": session.status,
        "opened_at": session.opened_at,
        "version": session.version,
        "customer_edit_window_minutes": session.unit.customer_edit_window_minutes,
        "points": [
            {"id": str(link.point_id), "name": link.point.label, "number": link.point.number}
            for link in session.point_links.all()
            if link.ended_at is None
        ],
        "participants": [
            {"id": str(person.id), "display_name": person.display_name, "active": person.active}
            for person in sorted(
                session.participants.all(), key=lambda person: (person.display_name, person.id)
            )
        ],
    }


def submit_order(identity, data, *, manual=False):
    actor = str(identity.staff.id if manual else identity.id)
    rate_limit("order-actor:" + actor, 10, 60)
    return _submit_order(identity, data, manual=manual)


@transaction.atomic
def _submit_order(identity, data, *, manual):
    if manual:
        require_permission(identity, "CREATE_MANUAL_ORDER")
        point_id = data["point_id"]
        unit = identity.staff.unit
        staff = identity.staff
        device = None
        actor = str(staff.id)
    else:
        point_id = identity.point_id
        unit = identity.point.unit
        staff = None
        device = identity
        actor = str(device.id)
    point = (
        ServicePoint.objects.select_for_update(of=("self",))
        .filter(id=point_id, unit=unit, active=True, unit__active=True, unit__company__active=True)
        .first()
    )
    if point is None:
        raise NotFound()
    link = SessionPoint.objects.filter(point=point, ended_at__isnull=True).first()
    session = (
        ServiceSession.objects.select_for_update(of=("self",)).get(id=link.session_id)
        if link
        else None
    )
    if session is not None and session.status not in OPEN_STATES:
        raise Conflict()
    if device is not None:
        device = require_device(device, point)
        if device.session_id is not None and (session is None or device.session_id != session.id):
            raise Conflict()
    previous = replay(
        actor, "MANUAL_ORDER" if manual else "ORDER", str(point.id), data["idempotency_key"], data
    )
    if previous:
        return previous.response
    # Deterministic product locks before group/option pricing prevent price races and deadlocks.
    list(
        Product.objects.select_for_update(of=("self",))
        .filter(unit=unit, id__in=[line["product_id"] for line in data["items"]])
        .order_by("id")
    )
    menu = point_menu(point)
    if point.menu_id is None:
        # Freeze legacy resolution before occupation; later menus cannot change this session's context.
        point.menu = menu
        point.save(update_fields=["menu"])
    snapshots = [quote(unit, line, lock=True, menu=menu) for line in data["items"]]
    if session is None:
        session = ServiceSession.objects.create(unit=unit)
        SessionPoint.objects.create(session=session, point=point)
    if OrderItem.objects.filter(batch__session=session).count() + len(data["items"]) > 500:
        raise ValidationError("Limite de itens por atendimento atingido.")
    DeviceAccess.objects.filter(
        point=point,
        session__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
        point_token_version=point.token_version,
    ).update(session=session)
    ServiceRequest.objects.filter(
        point=point, session__isnull=True, status__in=["OPEN", "ASSIGNED"]
    ).update(session=session)
    batch = OrderBatch.objects.create(
        session=session,
        origin_session=session,
        device=device,
        staff=staff,
        notes=data["notes"],
        channel="STAFF" if manual else "TABLE",
    )
    for line, snapshot in zip(data["items"], snapshots, strict=True):
        participant = None
        if line["participant_id"] is not None:
            participant = SessionParticipant.objects.filter(
                id=line["participant_id"], session=session, active=True
            ).first()
            if participant is None:
                raise ValidationError("Participante não disponível neste atendimento.")
        elif line["participant_name"]:
            participant = add_participant(session, line["participant_name"])
        item = OrderItem.objects.create(
            batch=batch,
            product_id=line["product_id"],
            sector_id=snapshot["sector_id"],
            participant=participant,
            quantity=line["quantity"],
            unit_price=Decimal(snapshot["unit_price"]),
            line_total=Decimal(snapshot["line_total"]),
            snapshot=snapshot,
            notes=line["notes"],
            fulfillment_mode=snapshot["fulfillment_mode"],
        )
        SelectedOption.objects.bulk_create(
            [
                SelectedOption(
                    item=item,
                    option_id=choice["id"],
                    name=choice["name"],
                    group_name=choice["group_name"],
                    additional_price=Decimal(choice["additional_price"]),
                )
                for choice in snapshot["options"]
            ]
        )
    session.version += 1
    session.save(update_fields=["version"])
    from .serializers import BatchOutput

    response = {"batch": BatchOutput(batch).data, "version": session.version}
    remember(
        unit,
        actor,
        "MANUAL_ORDER" if manual else "ORDER",
        str(point.id),
        data["idempotency_key"],
        data,
        response,
        201,
    )
    AuditEvent.objects.create(
        unit=unit, staff=staff, action="ORDER_CREATED", resource_id=str(batch.id)
    )
    from .production import publish

    publish(session, "ORDER_CREATED", [snapshot["sector_id"] for snapshot in snapshots])
    return response


def add_participant(session, name):
    existing = SessionParticipant.objects.filter(session=session, display_name=name).first()
    if existing is not None:
        if not existing.active:
            raise ValidationError("Participante desativado.")
        return existing
    if session.participants.count() >= 50:
        raise ValidationError("Limite de participantes atingido.")
    return SessionParticipant.objects.create(session=session, display_name=name)


@transaction.atomic
def create_participant(device, name):
    point = (
        ServicePoint.objects.select_for_update(of=("self",))
        .select_related("unit__company")
        .get(id=device.point_id)
    )
    device = require_device(device, point)
    if device.session_id is None:
        raise Conflict("O participante será criado ao confirmar o primeiro pedido.")
    session = (
        ServiceSession.objects.select_for_update(of=("self",))
        .filter(id=device.session_id, unit=device.point.unit, status__in=OPEN_STATES)
        .first()
    )
    if session is None:
        raise Conflict()
    participant = add_participant(session, name)
    AuditEvent.objects.create(
        unit=session.unit,
        device=device,
        action="PARTICIPANT_CONFIRMED",
        resource_id=str(participant.id),
    )
    session.version += 1
    session.save(update_fields=["version"])
    from .production import publish

    publish(session, "PARTICIPANT_CHANGED", [])
    return participant


@transaction.atomic
def remove_participant(device, identifier):
    rate_limit("participant-device:" + str(device.id), 20, 60)
    point = (
        ServicePoint.objects.select_for_update(of=("self",))
        .select_related("unit__company")
        .get(id=device.point_id)
    )
    device = require_device(device, point)
    session = (
        ServiceSession.objects.select_for_update()
        .filter(id=device.session_id, unit=point.unit, status__in=OPEN_STATES)
        .first()
    )
    if session is None:
        raise NotFound()
    participant = (
        SessionParticipant.objects.select_for_update()
        .filter(id=identifier, session=session)
        .first()
    )
    if participant is None:
        raise NotFound()
    if OrderItem.objects.filter(participant=participant).exists():
        raise Conflict(
            "Este participante possui pedidos confirmados e precisa permanecer no histórico."
        )
    if participant.active:
        participant.active = False
        participant.save(update_fields=["active"])
        session.version += 1
        session.save(update_fields=["version"])
        AuditEvent.objects.create(
            unit=session.unit,
            device=device,
            action="PARTICIPANT_REMOVED",
            resource_id=str(participant.id),
        )
        from .production import publish

        publish(session, "PARTICIPANT_CHANGED", [])
