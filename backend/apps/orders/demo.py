"""Additive local scenarios, built through the same identity/access/order services as the API."""

import json
import os
import secrets
from decimal import Decimal
from io import BytesIO
from ipaddress import ip_address
from uuid import NAMESPACE_URL, uuid5

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.test import RequestFactory
from PIL import Image

from apps.access.admission import decide_admission
from apps.access.models import DeviceAccess, DeviceAdmission, ServicePoint
from apps.access.services import cipher, create_point, exchange, point_url
from apps.catalog.models import Category, Menu, Option, OptionGroup, Product, ProductionSector
from apps.catalog.services import delete_image, save_image
from apps.identity.authentication import StaffIdentity
from apps.identity.management.commands.setup_platform import configure_platform
from apps.identity.management.commands.setup_unit import configure_unit
from apps.identity.models import IdempotencyRecord, PlatformOperator, Staff
from apps.identity.permissions import ROLE_DEFAULTS
from apps.identity.services import create_staff
from apps.organizations.models import Company, Unit

from .interventions import StaffItemCancelInput, change_item
from .models import (
    ExternalReceipt,
    OrderBatch,
    OrderItem,
    ServiceRequest,
    ServiceSession,
    SessionPoint,
)
from .production import SectorAssignmentInput, StatusInput, set_sectors, transition
from .serializers import OrderInput
from .service_requests import RequestInput, StaffRequestCommand, change_request, create_request
from .services import submit_order
from .settlement import (
    ExternalReceiptInput,
    ReceiptReverseInput,
    SessionCommand,
    change_settlement,
    session_totals,
)

RESTAURANT = {
    "Hambúrgueres": (
        ("Hambúrguer Clássico", "24.90"),
        ("Bacon Burger", "32.90"),
        ("Double Smash", "36.90"),
        ("Burger Especial", "42.90"),
        ("Chicken Burger", "29.90"),
    ),
    "Pizzas": (
        ("Mussarela", "49.90"),
        ("Calabresa", "54.90"),
        ("Frango com Catupiry", "59.90"),
        ("Portuguesa", "62.90"),
    ),
    "Porções": (
        ("Batata Frita", "24.90"),
        ("Batata com Bacon", "32.90"),
        ("Nuggets", "22.90"),
        ("Anéis de Cebola", "26.90"),
    ),
    "Bebidas": (
        ("Água Mineral", "5.00"),
        ("Coca-Cola Lata", "7.00"),
        ("Guaraná Lata", "7.00"),
        ("Suco Natural", "11.90"),
        ("Café Expresso", "6.90"),
        ("Milkshake", "18.90"),
    ),
    "Sobremesas": (
        ("Brownie", "16.90"),
        ("Pudim", "12.90"),
        ("Sorvete", "14.90"),
        ("Petit Gâteau", "24.90"),
    ),
}
HORIZONTE = {
    "Pratos": (
        ("Executivo vegetariano", "29.00"),
        ("Frango grelhado", "32.00"),
        ("Peixe do dia", "38.00"),
    ),
    "Lanches": (("Hambúrguer Clássico", "26.00"), ("Batata Frita", "17.00")),
    "Bebidas": (("Suco Natural", "9.00"), ("Água Mineral", "4.00"), ("Café Expresso", "5.00")),
    "Sobremesas": (("Brownie", "15.00"), ("Pudim", "12.00")),
}
UNIT_SPECS = (
    ("a", "centro", "Unidade Centro Demo"),
    ("a", "shopping", "Unidade Shopping Demo"),
    ("b", "principal", "Unidade Principal Demo"),
)
DESCRIPTIONS = {
    "Hambúrguer Clássico": "Pão brioche, hambúrguer bovino grelhado, queijo, alface, tomate e maionese da casa.",
    "Bacon Burger": "Hambúrguer bovino com bacon crocante, queijo derretido e molho da casa no pão brioche.",
    "Double Smash": "Dois discos de carne prensados na chapa, queijo, picles e molho especial.",
    "Burger Especial": "Hambúrguer artesanal, cebola caramelizada, queijo e combinação especial de molhos.",
    "Chicken Burger": "Filé de frango empanado, alface, tomate e maionese no pão macio.",
    "Mussarela": "Massa de fermentação lenta, molho de tomate, mussarela e orégano.",
    "Calabresa": "Molho de tomate, mussarela, calabresa fatiada e cebola.",
    "Frango com Catupiry": "Frango desfiado temperado, requeijão cremoso e mussarela sobre massa artesanal.",
    "Portuguesa": "Presunto, ovos, cebola, azeitonas e mussarela com molho de tomate.",
    "Batata Frita": "Batatas douradas e crocantes, preparadas na hora e finalizadas com sal.",
    "Batata com Bacon": "Porção de batatas fritas com queijo cremoso e bacon crocante.",
    "Nuggets": "Porção de pedaços de frango empanados e dourados, acompanhada de molho.",
    "Anéis de Cebola": "Anéis de cebola empanados, crocantes por fora e macios por dentro.",
    "Água Mineral": "Água mineral sem gás, garrafa individual de 500 ml.",
    "Coca-Cola Lata": "Refrigerante em lata de 350 ml, servido gelado.",
    "Guaraná Lata": "Refrigerante de guaraná em lata de 350 ml, servido gelado.",
    "Suco Natural": "Suco de limão preparado na hora, em copo de 400 ml. Personalize gelo e açúcar.",
    "Café Expresso": "Café de grãos selecionados, extraído na hora, em dose de 50 ml.",
    "Milkshake": "Bebida cremosa de sorvete de chocolate e leite, em copo de 400 ml.",
    "Brownie": "Brownie de chocolate com interior macio e casquinha delicada.",
    "Pudim": "Pudim de leite com calda de caramelo, em porção individual.",
    "Sorvete": "Duas bolas de sorvete cremoso, com calda de chocolate.",
    "Petit Gâteau": "Bolinho de chocolate com centro cremoso, acompanhado de sorvete.",
}


def reference(env, value):
    return uuid5(NAMESPACE_URL, f"tapserve.local.{env}/{value}")


def validate_destination(env):
    if (
        env not in {"dev", "qa"}
        or getattr(settings, "LOCAL_ENVIRONMENT", "") != env
        or settings.SETTINGS_MODULE != f"config.settings.{env}"
    ):
        raise CommandError(
            "Select the explicit dev/qa settings and TAPSERVE_ENV; no legacy destination allowed."
        )
    expected = (f"tapserve_{env}", f"tapserve_{env}_user")
    if (connection.settings_dict["NAME"], connection.settings_dict["USER"]) != expected:
        raise CommandError("Seed database/role mismatch.")
    if connection.settings_dict["HOST"] not in {"localhost", "127.0.0.1", "::1"}:
        raise CommandError("Seed requires the configured loopback PostgreSQL instance.")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_database(),current_user,inet_server_port(),host(inet_server_addr())"
        )
        database, user, port, address = cursor.fetchone()
        if (
            (database, user) != expected
            or port != int(connection.settings_dict["PORT"])
            or not ip_address(address).is_loopback
        ):
            raise CommandError("Live seed destination mismatch.")
        cursor.execute(
            "SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls FROM pg_roles WHERE rolname=current_user"
        )
        if cursor.fetchone()[0]:
            raise CommandError("Seed refuses an administrative application role.")
        cursor.execute(
            "SELECT EXISTS(SELECT 1 FROM pg_auth_members WHERE member=current_user::regrole), pg_get_userbyid(datdba)=current_user FROM pg_database WHERE datname=current_database()"
        )
        if cursor.fetchone() != (False, True):
            raise CommandError("Seed requires its own database and a role without memberships.")
        other = "tapserve_qa_user" if env == "dev" else "tapserve_dev_user"
        cursor.execute("SELECT has_database_privilege(%s,current_database(),'CONNECT')", [other])
        if cursor.fetchone()[0]:
            raise CommandError("Harden DEV and QA database permissions before seeding.")


def validated(serializer, data):
    parsed = serializer(data=data)
    parsed.is_valid(raise_exception=True)
    return parsed.validated_data


def identity(staff):
    return StaffIdentity(staff, True, frozenset(staff.permissions.values_list("code", flat=True)))


def credential_path(env):
    return settings.BASE_DIR.parent / ".local/environments" / env / "demo-credentials.enc"


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + secrets.token_hex(8) + ".tmp")
    try:
        with temporary.open("xb") as output:
            output.write(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_manifest(env):
    path = credential_path(env).with_name("seed-manifest.json")
    if path.exists():
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if (
            manifest.get("environment") != env
            or manifest.get("database") != connection.settings_dict["NAME"]
        ):
            raise CommandError("Seed manifest belongs to another environment/database.")
        return manifest
    if Company.objects.filter(
        pk__in=[reference(env, f"{env}-tapserve-demo"), reference(env, f"{env}-horizonte-demo")]
    ).exists():
        raise CommandError(
            "Existing demo has no seed manifest; restore its backup instead of adopting accounts by name."
        )
    return {
        "version": 1,
        "environment": env,
        "database": connection.settings_dict["NAME"],
        "refs": {},
        "scenarios": {},
    }


def recorded(model, manifest, key, **scope):
    identifier = manifest["refs"].get(key)
    if identifier is None:
        return None
    obj = model.objects.filter(pk=identifier, **scope).first()
    if obj is None:
        raise CommandError(
            "A recorded seed entity is missing or outside its scope; no replacement was created."
        )
    return obj


def credentials(env, *, dry_run):
    path = credential_path(env)
    accounts = json.loads(cipher().decrypt(path.read_bytes())) if path.exists() else {}
    # No plaintext credential fixture or PIN file; the existing local token key encrypts recovery.
    if (
        not path.exists()
        and Company.objects.filter(
            slug__in=[f"{env}-tapserve-demo", f"{env}-horizonte-demo"]
        ).exists()
    ):
        raise CommandError(
            "Demo credential vault missing; restore it instead of resetting existing identities."
        )
    keys = [
        "owner-a",
        "owner-b",
        "admin",
        "manager",
        "manager-shopping",
        "manager-horizonte",
        "platform",
    ]
    keys += [
        f"{company}-{unit}:{role}"
        for company, unit, _ in UNIT_SPECS
        for role in ("waiter", "kitchen", "bar", "cashier", "limited")
    ]
    keys.append("a-centro:waiter-2")
    pins = {value["pin"] for value in accounts.values()}
    changed = False
    for key in keys:
        if key in accounts:
            continue
        changed = True
        pin = f"{secrets.randbelow(10**8):08d}"
        while pin in pins:
            pin = f"{secrets.randbelow(10**8):08d}"
        pins.add(pin)
        accounts[key] = {"pin": pin}
        if ":" not in key:
            accounts[key]["password"] = secrets.token_urlsafe(32)
    if changed and not dry_run:
        atomic_write(path, cipher().encrypt(json.dumps(accounts).encode()))
    return accounts


def ensure(model, env, key, lookup, **defaults):
    identifier = reference(env, key)
    obj = model.objects.filter(pk=identifier).first()
    if obj is not None:
        for field, value in lookup.items():
            if hasattr(value, "pk") and getattr(obj, field + "_id") != value.pk:
                raise CommandError("A stable demo reference is outside its expected scope.")
        return obj, False
    if model.objects.filter(**lookup).exists():
        raise CommandError(
            f"Reserved demo reference collides with an existing {model.__name__}; no data overwritten."
        )
    obj = model(id=identifier, **lookup, **defaults)
    obj.full_clean()
    obj.save()
    return obj, True


def make_catalog(env, unit, actor, media_keys, *, dry_run):
    prefix = str(unit.id)
    menu, _ = ensure(Menu, env, prefix + "/menu", {"unit": unit, "name": "Cardápio Demo"})
    kitchen, _ = ensure(
        ProductionSector, env, prefix + "/kitchen", {"unit": unit, "name": "Cozinha Demo"}
    )
    bar, _ = ensure(ProductionSector, env, prefix + "/bar", {"unit": unit, "name": "Bar Demo"})
    products = {}
    data = RESTAURANT if unit.company_id == reference(env, f"{env}-tapserve-demo") else HORIZONTE
    for position, (category_name, rows) in enumerate(data.items()):
        category, _ = ensure(
            Category,
            env,
            prefix + "/" + category_name,
            {"menu": menu, "name": category_name},
            position=position,
        )
        for name, price in rows:
            product, created = ensure(
                Product,
                env,
                prefix + "/" + name,
                {"unit": unit, "name": name},
                category=category,
                production_sector=bar if category_name == "Bebidas" else kitchen,
                base_price=Decimal(price),
                description=DESCRIPTIONS.get(
                    name, "Prato do dia com arroz, feijão, legumes e acompanhamento da casa."
                ),
                long_description=DESCRIPTIONS.get(
                    name,
                    "Preparação individual com ingredientes selecionados e acompanhamentos da casa.",
                ),
                serving_info="1 pessoa",
                ingredients="Consulte a descrição e a equipe para personalizações.",
                allergen_info="Consulte a equipe sobre ingredientes e contaminação cruzada. Informação demonstrativa.",
                available=name != "Pudim",
                featured=name in {"Hambúrguer Clássico", "Burger Especial"},
            )
            products[name] = product
            image = {
                "Hambúrguer Clássico": "burger.png",
                "Batata Frita": "fries.png",
                "Suco Natural": "lemonade.png",
            }.get(name)
            if created and image and not dry_run:
                path = settings.BASE_DIR.parent / "assets/demo" / image
                if not path.is_file():
                    raise CommandError("The authorized bundled demo images must be available.")
                with Image.open(path) as source:
                    output = BytesIO()
                    source.convert("RGB").save(output, format="WEBP", quality=85)
                imported = save_image(
                    actor,
                    product.id,
                    SimpleUploadedFile(
                        image + ".webp", output.getvalue(), content_type="image/webp"
                    ),
                )
                media_keys.append(imported.image_key)
    classic = products["Hambúrguer Clássico"]
    for owner, name, kind, required, choices, applied_to in (
        (
            classic,
            "Ponto da carne",
            "SINGLE",
            True,
            (("Malpassado", "0.00"), ("Ao ponto", "0.00"), ("Bem-passado", "0.00")),
            [
                key
                for key in products
                if key in {"Hambúrguer Clássico", "Bacon Burger", "Double Smash", "Burger Especial"}
            ],
        ),
        (
            classic,
            "Adicionais",
            "MULTIPLE",
            False,
            (("Bacon", "5.00"), ("Queijo", "4.00"), ("Ovo", "3.00"), ("Hambúrguer extra", "9.00")),
            [
                key
                for key in products
                if key
                in {
                    "Hambúrguer Clássico",
                    "Bacon Burger",
                    "Double Smash",
                    "Burger Especial",
                    "Chicken Burger",
                }
            ],
        ),
        (
            classic,
            "Molhos",
            "MULTIPLE",
            False,
            (("Maionese", "0.00"), ("Barbecue", "0.00"), ("Mostarda", "0.00")),
            [
                key
                for key in products
                if key
                in {
                    "Hambúrguer Clássico",
                    "Bacon Burger",
                    "Double Smash",
                    "Burger Especial",
                    "Chicken Burger",
                    "Batata Frita",
                    "Nuggets",
                }
            ],
        ),
        (
            products["Suco Natural"],
            "Gelo",
            "SINGLE",
            False,
            (("Sem gelo", "0.00"), ("Com gelo", "0.00")),
            ["Suco Natural"],
        ),
        (
            products["Suco Natural"],
            "Açúcar",
            "SINGLE",
            False,
            (("Sem açúcar", "0.00"), ("Adoçado", "0.00")),
            ["Suco Natural"],
        ),
    ):
        group, created = ensure(
            OptionGroup,
            env,
            prefix + "/" + name,
            {"product": owner, "name": name},
            selection_type=kind,
            required=required,
            min_choices=int(required),
            max_choices=1 if kind == "SINGLE" else len(choices),
        )
        if created:
            for product_name in applied_to:
                products[product_name].applied_option_groups.add(group)
        for label, price in choices:
            ensure(
                Option,
                env,
                prefix + "/option/" + name + "/" + label,
                {"group": group, "name": label},
                additional_price=Decimal(price),
            )
    if "Mussarela" in products:
        pizza = products["Mussarela"]
        group, created = ensure(
            OptionGroup,
            env,
            prefix + "/pizza-size",
            {"product": pizza, "name": "Tamanho"},
            selection_type="SINGLE",
            required=True,
            min_choices=1,
            max_choices=1,
        )
        if created:
            for name in ("Mussarela", "Calabresa", "Frango com Catupiry", "Portuguesa"):
                products[name].applied_option_groups.add(group)
        for label, price in (("Média", "0.00"), ("Grande", "15.00")):
            ensure(
                Option,
                env,
                prefix + "/size/" + label,
                {"group": group, "name": label},
                additional_price=Decimal(price),
            )
    return menu, kitchen, bar, products


def make_point(env, unit, actor, menu, manifest, *, number=None, name="", kind="TABLE"):
    key = reference(env, f"{unit.id}/point/{number or kind}")
    point = recorded(ServicePoint, manifest, str(key), unit=unit)
    if point:
        return point
    previous = IdempotencyRecord.objects.filter(unit=unit, action="CREATE_POINT", key=key).first()
    if previous:
        point = ServicePoint.objects.get(id=previous.response["id"], unit=unit)
        manifest["refs"][str(key)] = str(point.id)
        return point
    lookup = {"unit": unit, "number": number} if number else {"unit": unit, "name": name}
    if ServicePoint.objects.filter(**lookup).exists():
        raise CommandError("Demo service point collides with existing data; nothing was changed.")
    response = create_point(
        actor,
        {
            "idempotency_key": key,
            "menu": menu.id,
            "number": number,
            "name": name,
            "type": kind,
            "nfc_enabled": True,
            "qr_enabled": True,
        },
    )
    point = ServicePoint.objects.get(id=response["id"])
    manifest["refs"][str(key)] = str(point.id)
    return point


def admitted_device(point, actor):
    request = browser_request(point)
    token = point_url(point).rsplit("/", 1)[1]
    admission, _ = exchange(request, token)
    if not isinstance(admission, DeviceAdmission):
        raise CommandError("Expected a fresh demo admission.")
    decide_admission(
        actor,
        admission.id,
        {"idempotency_key": uuid5(admission.id, "approve"), "status": "APPROVED"},
    )
    device, _ = exchange(request, token)
    if not isinstance(device, DeviceAccess):
        raise CommandError("Demo device approval did not issue access.")
    return device


def browser_request(point):
    # Synthetic browsers keep their own loopback address and nonce; real rate limits remain active.
    address = "127." + ".".join(str(part) for part in point.id.bytes[:3])
    request = RequestFactory().post("/api/v1/public/access/", REMOTE_ADDR=address)
    request.session = SessionStore()
    request.session["tapserve_browser_nonce"] = secrets.token_urlsafe(32)
    return request


def new_batch(env, scenario, point, actor, products, *, count=1):
    device = admitted_device(point, actor)
    classic = products["Hambúrguer Clássico"]
    choices = list(
        Option.objects.filter(group__product=classic, name__in=["Ao ponto", "Queijo"]).values_list(
            "id", flat=True
        )
    )
    rows = [
        {
            "product_id": str(classic.id),
            "quantity": 1,
            "option_ids": [str(value) for value in choices],
            "participant_name": "Cliente Alfa Demo",
            "notes": "Sem cebola; observação fictícia.",
        }
    ]
    if count == 2:
        rows.append(
            {
                "product_id": str(products["Suco Natural"].id),
                "quantity": 2,
                "option_ids": [],
                "participant_name": "Cliente Beta Demo",
            }
        )
    data = validated(
        OrderInput,
        {
            "idempotency_key": str(reference(env, scenario + "/order")),
            "notes": "Pedido sintético de demonstração.",
            "items": rows,
        },
    )
    result = submit_order(device, data)
    return OrderBatch.objects.get(id=result["batch"]["id"]), device


def advance(actor, batch, target):
    route = ["NEW", "ACCEPTED", "PREPARING", "READY", "DELIVERING", "DELIVERED"]
    for item in batch.items.all():
        for state in route[1 : route.index(target) + 1]:
            transition(
                actor,
                item.id,
                validated(
                    StatusInput,
                    {
                        "idempotency_key": str(uuid5(item.id, state)),
                        "expected_status": item.status,
                        "status": state,
                    },
                ),
            )
            item.refresh_from_db()


def call(actor, device, kind, target="OPEN"):
    result = create_request(
        device,
        validated(
            RequestInput,
            {
                "idempotency_key": str(uuid5(device.id, kind)),
                "kind": kind,
                "message": "Solicitação sintética de demonstração.",
            },
        ),
    )
    for state in (
        ["ASSIGNED", "RESOLVED"]
        if target == "RESOLVED"
        else ["ASSIGNED"]
        if target == "ASSIGNED"
        else ["CANCELLED"]
        if target == "CANCELLED"
        else []
    ):
        row = ServiceRequest.objects.get(id=result["id"])
        change_request(
            actor,
            row.id,
            validated(
                StaffRequestCommand,
                {
                    "idempotency_key": str(uuid5(row.id, state)),
                    "expected_status": row.status,
                    "status": state,
                    "reason": "Atendimento de demonstração.",
                },
            ),
            manual=True,
        )


def settle(actor, batch, point, *, partial=False, close=False, method="PIX", correction=False):
    session = ServiceSession.objects.get(id=batch.session_id)
    amount = session_totals(session)[0]
    if partial:
        amount = (amount / 2).quantize(Decimal("0.01"))
    change_settlement(
        actor,
        session.id,
        validated(
            ExternalReceiptInput,
            {
                "idempotency_key": str(uuid5(session.id, "receipt")),
                "expected_version": session.version,
                "point_id": str(point.id),
                "amount": str(amount),
                "method": method,
                "reason": "Recebimento externo fictício declarado; sem transação financeira.",
            },
        ),
        "RECEIPT",
    )
    if correction:
        receipt = session.external_receipts.get(reverses__isnull=True)
        session.refresh_from_db()
        change_settlement(
            actor,
            session.id,
            validated(
                ReceiptReverseInput,
                {
                    "idempotency_key": str(uuid5(session.id, "reverse-receipt")),
                    "expected_version": session.version,
                    "reason": "Correção demonstrativa do método declarado, sem movimentação de dinheiro.",
                },
            ),
            "REVERSE",
            receipt_id=receipt.id,
        )
        session.refresh_from_db()
        change_settlement(
            actor,
            session.id,
            validated(
                ExternalReceiptInput,
                {
                    "idempotency_key": str(uuid5(session.id, "corrected-receipt")),
                    "expected_version": session.version,
                    "point_id": str(point.id),
                    "amount": str(amount),
                    "method": "CARD",
                    "reason": "Recebimento externo corretamente declarado após reversão do lançamento.",
                },
            ),
            "RECEIPT",
        )
    if close:
        session.refresh_from_db()
        change_settlement(
            actor,
            session.id,
            validated(
                SessionCommand,
                {
                    "idempotency_key": str(uuid5(session.id, "close")),
                    "expected_version": session.version,
                    "reason": "Encerramento sintético de demonstração.",
                },
            ),
            "CLOSE",
        )


def scenarios(env, unit, actor, points, products, manifest, *, primary):
    skipped = 0
    targets = (
        {
            2: "NEW",
            3: "PREPARING",
            4: "READY",
            5: "DELIVERED",
            6: "DELIVERED",
            7: "DELIVERED",
            8: "NEW",
            9: "NEW",
            10: "DELIVERED",
        }
        if primary
        else {2: "NEW", 3: "PREPARING", 4: "DELIVERED"}
    )
    for number, target in targets.items():
        scenario = f"{unit.id}/scenario/{number}"
        order_key = reference(env, scenario + "/order")
        previous = IdempotencyRecord.objects.filter(
            unit=unit, action="ORDER", key=order_key
        ).first()
        if previous:
            batch = OrderBatch.objects.get(id=previous.response["batch"]["id"], session__unit=unit)
            manifest["scenarios"][scenario] = str(batch.session_id)
            skipped += 1
            continue
        point = points[number]
        if SessionPoint.objects.filter(point=point).exists():
            raise CommandError(
                "A demo scenario point has existing service history; refusing to overwrite it."
            )
        batch, device = new_batch(
            env, scenario, point, actor, products, count=2 if number in (2, 8) else 1
        )
        advance(actor, batch, target)
        if number in (3, 4) or not primary and number == 2:
            call(
                actor,
                device,
                {2: "ATTENDANT", 3: "CLEANING", 4: "CUTLERY"}[number],
                {2: "OPEN", 3: "ASSIGNED", 4: "RESOLVED"}[number],
            )
        if primary and number == 2:
            extra, _ = new_batch(env, scenario + "/cancel", point, actor, products)
            item = extra.items.get()
            change_item(
                actor,
                item.id,
                validated(
                    StaffItemCancelInput,
                    {
                        "idempotency_key": str(uuid5(item.id, "cancel")),
                        "expected_version": item.version,
                        "reason": "Cliente desistiu; cancelamento de demonstração.",
                    },
                ),
                manual=True,
                cancel=True,
            )
        if primary and number == 6:
            call(actor, device, "CHECK")
        if primary and number == 5:
            settle(actor, batch, point, method="MONEY", correction=True)
        if primary and number in (7, 10):
            settle(
                actor,
                batch,
                point,
                partial=number == 7,
                close=number == 10,
                method="PIX" if number == 7 else "MONEY",
            )
        if primary and number == 8:
            call(actor, device, "NAPKIN", "CANCELLED")
            extra, _ = new_batch(env, scenario + "/second-participant", point, actor, products)
            advance(actor, extra, "ACCEPTED")
        if primary and number == 9:
            call(actor, device, "ATTENDANT")
        if primary and number == 10:
            reused, _ = new_batch(env, scenario + "/reuse", point, actor, products)
            advance(actor, reused, "DELIVERED")
            settle(actor, reused, point, close=True, method="CARD")
        manifest["scenarios"][scenario] = str(batch.session_id)
    pending_key = f"{unit.id}/pending"
    if pending_key not in manifest["refs"]:
        point = points[9 if primary else 1]
        # A committed real admission also recovers a manifest write interrupted after DB commit.
        admission = DeviceAdmission.objects.filter(
            point=point, status="PENDING", device__isnull=True
        ).first()
        if admission is None:
            request = browser_request(point)
            admission, _ = exchange(request, point_url(point).rsplit("/", 1)[1])
        manifest["refs"][pending_key] = str(admission.id)
    return skipped


def privileged(env, unit, key, role, name, accounts, manifest):
    ref = f"{unit.id}/staff/{key}"
    staff = recorded(Staff, manifest, ref, unit=unit)
    if staff is None:
        account = accounts[key]
        staff = configure_unit(
            dict(
                company=unit.company.slug,
                company_name=unit.company.name,
                unit=unit.slug,
                unit_name=unit.name,
                username=f"{env}-{key}",
                name=name,
                role=role,
                refresh_role_grants=False,
            ),
            account["password"],
            account["pin"],
        )
        manifest["refs"][ref] = str(staff.id)
    return staff


def summary(units, platform=None):
    user_ids = set(
        Staff.objects.filter(unit__in=units, user__isnull=False).values_list("user_id", flat=True)
    )
    if platform is not None:
        user_ids.add(platform.pk)
    return {
        "companies": Company.objects.filter(units__in=units).distinct().count(),
        "units": len(units),
        "users": len(user_ids),
        "staff": Staff.objects.filter(unit__in=units).count(),
        "administrators": Staff.objects.filter(
            unit__in=units, role__name__in=["OWNER", "ADMIN", "MANAGER"]
        ).count(),
        "operational_staff": Staff.objects.filter(unit__in=units)
        .exclude(role__name__in=["OWNER", "ADMIN", "MANAGER"])
        .count(),
        "points": ServicePoint.objects.filter(unit__in=units).count(),
        "tables": ServicePoint.objects.filter(unit__in=units, type="TABLE").count(),
        "menus": Menu.objects.filter(unit__in=units).count(),
        "categories": Category.objects.filter(menu__unit__in=units).count(),
        "products": Product.objects.filter(unit__in=units).count(),
        "option_groups": OptionGroup.objects.filter(product__unit__in=units).count(),
        "options": Option.objects.filter(group__product__unit__in=units).count(),
        "batches": OrderBatch.objects.filter(session__unit__in=units).count(),
        "items": OrderItem.objects.filter(batch__session__unit__in=units).count(),
        "sessions": ServiceSession.objects.filter(unit__in=units).count(),
        "requests": ServiceRequest.objects.filter(unit__in=units).count(),
        "admissions": DeviceAdmission.objects.filter(point__unit__in=units).count(),
        "external_receipts": ExternalReceipt.objects.filter(session__unit__in=units).count(),
    }


def seed_environment(env, *, dry_run=False):
    validate_destination(env)
    media_keys: list[str] = []
    try:
        with transaction.atomic():
            result, manifest = populate(env, media_keys, dry_run=dry_run)
            if dry_run:
                transaction.set_rollback(True)
    except Exception:
        # Remove only files imported by this rolled-back seed, never an existing media directory.
        for key in media_keys:
            delete_image(key)
        raise
    if not dry_run:
        path = credential_path(env).with_name("seed-manifest.json")
        serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode()
        if not path.exists() or path.read_bytes() != serialized:
            atomic_write(path, serialized)
    return result


def populate(env, media_keys, *, dry_run):
    with transaction.atomic():
        # All domain mutations share a commit; the separate manifest identifies existing bootstrap accounts.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(%s)",
                [int.from_bytes(reference(env, "seed").bytes[:8], "big", signed=True)],
            )
        accounts = credentials(env, dry_run=dry_run)
        manifest = load_manifest(env)
        existing_units = list(
            Unit.objects.filter(
                pk__in=[
                    reference(
                        env, f"{env}-{'tapserve' if company == 'a' else 'horizonte'}-demo/{slug}"
                    )
                    for company, slug, _ in UNIT_SPECS
                ]
            )
        )
        operator = recorded(PlatformOperator, manifest, "platform")
        before = summary(existing_units, operator.user if operator else None)
        skipped = 0
        units = []
        for company_code, slug, name in UNIT_SPECS:
            company_slug = f"{env}-{'tapserve' if company_code == 'a' else 'horizonte'}-demo"
            company, _ = ensure(
                Company,
                env,
                company_slug,
                {"slug": company_slug},
                name="TapServe Demo" if company_code == "a" else "Restaurante Horizonte Demo",
            )
            unit, _ = ensure(
                Unit,
                env,
                company_slug + "/" + slug,
                {"company": company, "slug": slug},
                name=name,
                table_takeaway_enabled=True,
                leftover_packaging_enabled=True,
                menu_layout="COMPACT" if slug == "shopping" else "EDITORIAL",
            )
            units.append(unit)
            manifest["refs"][f"unit:{company_code}-{slug}"] = str(unit.id)
            owner = privileged(
                env,
                unit,
                "owner-" + company_code,
                "OWNER",
                "Proprietário Demo " + company_code.upper(),
                accounts,
                manifest,
            )
            actor = identity(owner)
            if company_code == "a" and slug == "centro":
                for key, role in (("admin", "ADMIN"), ("manager", "MANAGER")):
                    privileged(
                        env,
                        unit,
                        key,
                        role,
                        "Administrador Demo" if key == "admin" else "Gerente 01",
                        accounts,
                        manifest,
                    )
            else:
                key = "manager-shopping" if slug == "shopping" else "manager-horizonte"
                privileged(
                    env,
                    unit,
                    key,
                    "MANAGER",
                    "Gerente Shopping" if slug == "shopping" else "Gerente Horizonte",
                    accounts,
                    manifest,
                )
            menu, kitchen, bar, products = make_catalog(
                env, unit, actor, media_keys, dry_run=dry_run
            )
            staff_specs = [
                (
                    "waiter",
                    "WAITER",
                    "Atendente 01" if slug == "centro" else "Atendente " + slug.capitalize(),
                ),
                (
                    "kitchen",
                    "KITCHEN",
                    "Produção 01" if slug == "centro" else "Produção " + slug.capitalize(),
                ),
                ("bar", "BAR", "Bar Demo"),
                ("cashier", "CASHIER", "Caixa Demo"),
                ("limited", "WAITER", "Atendente Restrito"),
            ]
            if slug == "centro":
                staff_specs.append(("waiter-2", "WAITER", "Atendente 02"))
            for key, role, name in staff_specs:
                ref = f"{unit.id}/staff/{key}"
                staff = recorded(Staff, manifest, ref, unit=unit)
                if staff is None:
                    idempotency_key = reference(env, ref)
                    previous = IdempotencyRecord.objects.filter(
                        unit=unit, action="CREATE_STAFF", key=idempotency_key
                    ).first()
                    if previous:
                        staff = Staff.objects.get(pk=previous.response["id"], unit=unit)
                        manifest["refs"][ref] = str(staff.id)
                        continue
                    if Staff.objects.filter(unit=unit, login_code="demo-" + key).exists():
                        raise CommandError(
                            "Existing staff code has no seed ownership record; no account was overwritten."
                        )
                    staff = create_staff(
                        actor,
                        {
                            "role_id": unit.roles.get(name=role).id,
                            "idempotency_key": idempotency_key,
                            "name": name,
                            "login_code": "demo-" + key,
                            "pin": accounts[f"{company_code}-{slug}:{key}"]["pin"],
                            "permissions": list(ROLE_DEFAULTS[role])
                            if key != "limited"
                            else ["VIEW_OPERATION"],
                        },
                    )
                    if key in {"kitchen", "bar"}:
                        set_sectors(
                            actor,
                            staff.id,
                            validated(
                                SectorAssignmentInput,
                                {"sector_ids": [str((kitchen if key == "kitchen" else bar).id)]},
                            ),
                        )
                    manifest["refs"][ref] = str(staff.id)
            points = {
                number: make_point(env, unit, actor, menu, manifest, number=number, name="")
                for number in range(1, 11 if slug == "centro" else 6)
            }
            if slug == "centro":
                demo = make_point(env, unit, actor, menu, manifest, number=11, name="Mesa Demo")
                manifest["refs"]["mesa-demo"] = str(demo.id)
                for kind, label in (("COUNTER", "Balcão 01"), ("PICKUP", "Retirada 01")):
                    make_point(env, unit, actor, menu, manifest, kind=kind, name=label)
            skipped += scenarios(
                env, unit, actor, points, products, manifest, primary=slug == "centro"
            )
        if operator is None:
            platform = configure_platform(f"{env}-platform", accounts["platform"]["password"])
            manifest["refs"]["platform"] = str(platform.pk)
        else:
            platform = operator.user
        result = summary(units, platform)
        return {
            "total": result,
            "created": {key: result[key] - before[key] for key in result},
            "reused": before,
            "ignored_scenarios": skipped,
        }, manifest
