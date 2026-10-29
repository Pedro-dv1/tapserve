"""Shared server quote and bounded image normalization for actual ordering."""

import hashlib
import logging
import uuid
import warnings
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.db.models import Q
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import NotFound, ValidationError

from apps.identity.models import AuditEvent
from apps.identity.permissions import require_permission
from apps.identity.services import rate_limit
from apps.organizations.models import Unit
from common.idempotency import Conflict, remember, replay

from .models import Menu, Option, OptionGroup, Product


def publish_catalog_change(unit):
    """One unit catalog invalidation, delivered by PostgreSQL only after commit."""
    from apps.access.models import ServicePoint
    from apps.orders.models import DomainEvent

    point_id = (
        ServicePoint.objects.filter(unit=unit, active=True).values_list("id", flat=True).first()
    )
    if point_id is not None:
        DomainEvent.objects.create(unit=unit, point_id=point_id, kind="CATALOG_CHANGED", version=1)


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def point_menu(point):
    """Legacy points resolve only when exactly one active menu exists in their unit."""
    menus = Menu.objects.filter(unit_id=point.unit_id, active=True)
    if point.menu_id:
        menu = menus.filter(id=point.menu_id).first()
    else:
        candidates = list(menus.order_by("id")[:2])
        menu = candidates[0] if len(candidates) == 1 else None
    if menu is None:
        raise ValidationError("Este ponto precisa de um cardápio ativo definido pela gestão.")
    return menu


def available_products(unit, menu=None):
    products = Product.objects.filter(
        unit=unit,
        active=True,
        available=True,
        category__active=True,
        category__menu__active=True,
        production_sector__active=True,
    )
    return products.filter(category__menu=menu) if menu is not None else products


def quote(unit, data: dict, *, lock: bool = False, menu=None) -> dict:
    products = available_products(unit, menu)
    if lock:
        products = products.select_for_update(of=("self",))
    product = (
        products.select_related("production_sector", "category__menu")
        .filter(id=data["product_id"])
        .first()
    )
    if product is None:
        raise ValidationError("Produto não disponível.")
    mode = data.get("fulfillment_mode", "DINE_IN")
    if mode not in {"DINE_IN", "TAKEAWAY"}:
        raise ValidationError({"fulfillment_mode": "Modalidade inválida."})
    if mode == "TAKEAWAY":
        if not unit.table_takeaway_enabled:
            raise ValidationError(
                {"fulfillment_mode": "Para levar está desativado nesta unidade."},
                code="TAKEAWAY_DISABLED",
            )
        if not product.takeaway_allowed:
            raise ValidationError(
                {"fulfillment_mode": "Este produto não está disponível para levar."},
                code="TAKEAWAY_NOT_ALLOWED",
            )
    ids = data["option_ids"]
    if len(ids) != len(set(ids)):
        raise ValidationError("Opção duplicada.")
    groups = OptionGroup.objects.filter(products=product, product__unit=unit, active=True).order_by(
        "id"
    )
    selected_groups = list(groups.select_for_update(of=("self",)) if lock else groups)
    options = Option.objects.filter(
        Q(group_id__in=[group.id for group in selected_groups])
        | Q(id__in=product.individual_options.values("id")),
        group__product__unit=unit,
        active=True,
        available=True,
    ).order_by("id")
    if lock:
        options = options.select_for_update(of=("self",))
    selected_options = [option for option in options if option.id in ids]
    if len(selected_options) != len(ids):
        raise ValidationError("Opção não disponível.")
    for group in selected_groups:
        count = sum(option.group_id == group.id for option in selected_options)
        if count < group.min_choices or count > group.max_choices:
            raise ValidationError("Confira as opções obrigatórias e seus limites.")
    unit_price = product.base_price + sum(
        (option.additional_price for option in selected_options), Decimal("0")
    )
    if "expected_unit_price" in data and unit_price != data["expected_unit_price"]:
        raise Conflict(
            "O preço mudou. Abra o item no carrinho e confira o novo valor antes de confirmar.",
            code="PRICE_CHANGED",
        )
    return {
        "product_id": str(product.id),
        "name": product.name,
        "unit_price": money(unit_price),
        "line_total": money(unit_price * data["quantity"]),
        "currency": "BRL",
        "quantity": data["quantity"],
        "fulfillment_mode": mode,
        "sector_id": str(product.production_sector_id),
        "sector_name": product.production_sector.name,
        "category_name": product.category.name,
        "options": [
            {
                "id": str(option.id),
                "name": option.name,
                "group_name": next(
                    (group.name for group in selected_groups if group.id == option.group_id),
                    "Adicionais",
                ),
                "additional_price": money(option.additional_price),
            }
            for option in selected_options
        ],
    }


def normalize_image(upload, *, preserve_alpha=False) -> bytes:
    limit = settings.PRODUCT_IMAGE_MAX_BYTES
    if upload.size > limit:
        raise ValidationError({"image": "Imagem excede o limite de envio."})
    raw = upload.read(limit + 1)
    if len(raw) > limit:
        raise ValidationError({"image": "Imagem excede o limite de envio."})
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw), formats=["JPEG", "PNG", "WEBP"]) as image:
                if image.width * image.height > 4_000_000 or getattr(image, "n_frames", 1) != 1:
                    raise ValidationError({"image": "Use uma imagem estática de até 4 megapixels."})
                image.verify()
            with Image.open(BytesIO(raw), formats=["JPEG", "PNG", "WEBP"]) as image:
                image.load()
                clean = ImageOps.exif_transpose(image).convert("RGBA" if preserve_alpha else "RGB")
                clean.thumbnail((1600, 1600))
                output = BytesIO()
                clean.save(output, format="WEBP", quality=85, exif=b"", icc_profile=None)
                result = output.getvalue()
                if len(result) > limit:
                    raise ValidationError({"image": "Imagem normalizada excede o limite de envio."})
                return result
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        ValueError,
    ) as error:
        raise ValidationError({"image": "Arquivo de imagem inválido."}) from error


def save_image(identity, identifier, upload):
    require_permission(identity, "MANAGE_MENU")
    # Authorize before decoding or writing any file, then recheck under the row lock.
    if not Product.objects.filter(id=identifier, unit=identity.staff.unit).exists():
        raise NotFound()
    normalized = normalize_image(upload)
    key = default_storage.save(
        f"products/{identity.staff.unit_id}/{uuid.uuid4()}.webp", ContentFile(normalized)
    )
    try:
        with transaction.atomic():
            require_permission(identity, "MANAGE_MENU")
            product = (
                Product.objects.select_for_update()
                .filter(id=identifier, unit=identity.staff.unit)
                .first()
            )
            if product is None:
                raise NotFound()
            old = product.image_key
            product.image_key = key
            product.save(update_fields=["image_key"])
            publish_catalog_change(product.unit)
            AuditEvent.objects.create(
                unit=identity.staff.unit,
                staff=identity.staff,
                action="PRODUCT_IMAGE_UPDATED",
                resource_id=str(product.id),
            )
            if old:
                transaction.on_commit(lambda: delete_image(old), robust=True)
    except Exception:
        default_storage.delete(key)
        raise
    return product


def delete_image(key):
    if key:
        try:
            default_storage.delete(key)
        except Exception as error:
            logging.getLogger("tapserve.media").error(
                "image_cleanup_failed", extra={"error_type": type(error).__name__}
            )


def write_product(identity, serializer, identifier=None):
    """One product mutation, including its normalized image and durable retry result."""
    require_permission(identity, "MANAGE_MENU")
    values = dict(serializer.validated_data)
    upload = values.pop("image", None)
    remove = values.pop("remove_image", False)
    video = values.pop("video", None)
    remove_video = values.pop("remove_video", False)
    key = values.pop("idempotency_key", None)
    group_ids = values.pop("option_group_ids", None)
    option_ids = values.pop("individual_option_ids", None)
    if upload and remove:
        raise ValidationError({"image": "Selecione uma imagem ou remova a atual."})
    if video and remove_video:
        raise ValidationError({"video": "Envie um vídeo ou remova o atual."})
    if video:
        from .video import validate_video

        rate_limit("video-staff:" + str(identity.staff.id), 10, 60)
        video_extension = validate_video(video)
    if upload:
        rate_limit("image-staff:" + str(identity.staff.id), 20, 60)
    normalized = normalize_image(upload) if upload else None
    body = {name: getattr(value, "pk", value) for name, value in values.items()}
    body.update(
        remove_image=remove,
        image_digest=hashlib.sha256(normalized).hexdigest() if normalized else None,
        option_group_ids=group_ids,
        individual_option_ids=option_ids,
    )
    video_digest = hashlib.sha256()
    if video:
        for chunk in video.chunks():
            video_digest.update(chunk)
        video.seek(0)
    if video or remove_video:
        body.update(
            remove_video=remove_video, video_digest=video_digest.hexdigest() if video else None
        )
    stored = None
    stored_video = None
    try:
        with transaction.atomic():
            Unit.objects.select_for_update().get(id=identity.staff.unit_id)
            require_permission(identity, "MANAGE_MENU")
            resource = str(identifier or identity.staff.unit_id)
            actor = str(identity.staff.id)
            if key:
                previous = replay(actor, "PRODUCT_WRITE", resource, key, body)
                if previous:
                    return previous.response
            product = None
            if identifier:
                product = (
                    Product.objects.select_for_update()
                    .filter(id=identifier, unit=identity.staff.unit)
                    .first()
                )
                if product is None:
                    raise NotFound()
            old = product.image_key if product else ""
            old_video = product.video_key if product else ""
            if normalized:
                stored = default_storage.save(
                    f"products/{identity.staff.unit_id}/{uuid.uuid4()}.webp",
                    ContentFile(normalized),
                )
            if video:
                stored_video = default_storage.save(
                    f"products/{identity.staff.unit_id}/{uuid.uuid4()}.{video_extension}", video
                )
            if product is None:
                product = Product(unit=identity.staff.unit, **values)
            else:
                for name, value in values.items():
                    setattr(product, name, value)
            if stored or remove:
                product.image_key = stored or ""
            if stored_video or remove_video:
                product.video_key = stored_video or ""
            product.save()
            # ASVS 8.2.2/8.4.1: recheck association ownership at the write boundary.
            if group_ids is not None:
                groups = OptionGroup.objects.filter(
                    id__in=group_ids, product__unit=identity.staff.unit
                )
                if groups.count() != len(group_ids):
                    raise ValidationError("Grupo indisponível nesta unidade.")
                product.applied_option_groups.set(groups)
            if option_ids is not None:
                options = Option.objects.filter(
                    id__in=option_ids, group__product__unit=identity.staff.unit
                )
                if options.count() != len(option_ids):
                    raise ValidationError("Opção indisponível nesta unidade.")
                product.individual_options.set(options)
            publish_catalog_change(product.unit)
            AuditEvent.objects.create(
                unit=product.unit,
                staff=identity.staff,
                action="CATALOG_UPDATED" if identifier else "CATALOG_CREATED",
                resource_id=str(product.id),
                reason="products",
            )
            from .serializers import ProductOutput

            result = dict(ProductOutput(product).data)
            if key:
                remember(
                    product.unit,
                    actor,
                    "PRODUCT_WRITE",
                    resource,
                    key,
                    body,
                    result,
                    200 if identifier else 201,
                )
            if old and (stored or remove):
                transaction.on_commit(lambda: delete_image(old), robust=True)
            if old_video and (stored_video or remove_video):
                transaction.on_commit(lambda: delete_image(old_video), robust=True)
            return result
    except IntegrityError as error:
        if stored_video:
            delete_image(stored_video)
        if stored:
            delete_image(stored)
        raise ValidationError("Cadastro viola uma regra de integridade.") from error
    except Exception:
        if stored_video:
            delete_image(stored_video)
        if stored:
            delete_image(stored)
        raise
