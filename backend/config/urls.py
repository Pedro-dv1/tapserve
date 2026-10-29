from django.conf import settings
from django.urls import path
from drf_spectacular.views import SpectacularAPIView

from apps.access.views import (
    AccessView,
    DeviceRevokeView,
    PointDetailView,
    PointDevicesView,
    PointIdentifierView,
    PointListView,
    PointMenuOptionDetailView,
    PointMenuOptionsView,
    PointPresenceView,
    PointQrView,
    PointUrlView,
    PublicContextView,
    PublicUnitLogoView,
)
from apps.catalog.gallery import ProductPhotosView, ProductPhotoView, PublicProductPhotoView
from apps.catalog.views import (
    CATALOG,
    CatalogDetailView,
    CatalogView,
    ProductImageView,
    ProductVideoView,
    PublicCategoriesView,
    PublicMenuView,
    PublicProductImageView,
    PublicProductVideoView,
    PublicProductView,
    PublicQuoteView,
)
from apps.identity.platform import (
    PlatformCompanyView,
    PlatformLoginView,
    PlatformLogoutView,
    PlatformMeView,
    PlatformUnitView,
)
from apps.identity.views import (
    LogoutView,
    PasswordLoginView,
    PinLoginView,
    RoleListView,
    StaffDetailView,
    StaffListView,
    StaffMeView,
    StaffUnitsView,
)
from apps.orders.interventions import (
    OrderPolicyView,
    PublicItemCancelView,
    PublicItemView,
    StaffItemCancelView,
    StaffItemView,
    StaffProductChoicesView,
)
from apps.orders.production import (
    ItemStatusView,
    ProductionItemsView,
    SectorOptionsView,
    StaffSectorsView,
)
from apps.orders.service_requests import (
    PublicRequestCancelView,
    PublicRequestReceiptView,
    PublicRequestsView,
    StaffRequestStatusView,
    StaffRequestsView,
)
from apps.orders.views import (
    ManualOrderView,
    PublicOrderReceiptView,
    PublicOrdersView,
    PublicParticipantDetailView,
    PublicParticipantsView,
    PublicSessionView,
    StaffDeliveryItemsView,
    StaffOperationView,
    StaffPointMenuView,
    StaffSessionOrdersView,
    StaffTablesView,
)
from apps.organizations.views import UnitLogoImageView, UnitLogoView
from common.api import CsrfView, HealthView, not_found, server_error

urlpatterns = [
    path("api/v1/admin/products/<uuid:identifier>/photos/", ProductPhotosView.as_view()),
    path(
        "api/v1/admin/products/<uuid:identifier>/photos/<uuid:photo_id>/",
        ProductPhotoView.as_view(),
    ),
    path(
        "api/v1/public/products/<uuid:identifier>/photos/<uuid:photo_id>/",
        PublicProductPhotoView.as_view(),
    ),
    path("api/v1/admin/unit-logo/", UnitLogoView.as_view()),
    path("api/v1/admin/unit-logo/image/", UnitLogoImageView.as_view()),
    path("api/v1/public/unit-logo/image/", PublicUnitLogoView.as_view()),
    path(
        "api/v1/admin/service-points/<uuid:identifier>/identifier/", PointIdentifierView.as_view()
    ),
    path("api/v1/admin/service-points/<uuid:identifier>/presence/", PointPresenceView.as_view()),
    path("api/v1/admin/products/<uuid:identifier>/video/", ProductVideoView.as_view()),
    path("api/v1/public/products/<uuid:identifier>/video/", PublicProductVideoView.as_view()),
    path("api/v1/staff/products/<uuid:identifier>/choices/", StaffProductChoicesView.as_view()),
    path("api/v1/public/service-request-receipts/<uuid:key>/", PublicRequestReceiptView.as_view()),
    path("api/v1/admin/order-policy/", OrderPolicyView.as_view()),
    path("api/v1/public/items/<uuid:identifier>/", PublicItemView.as_view()),
    path("api/v1/public/items/<uuid:identifier>/cancel/", PublicItemCancelView.as_view()),
    path("api/v1/staff/items/<uuid:identifier>/", StaffItemView.as_view()),
    path("api/v1/staff/items/<uuid:identifier>/cancel/", StaffItemCancelView.as_view()),
    path("api/v1/public/service-requests/", PublicRequestsView.as_view()),
    path(
        "api/v1/public/service-requests/<uuid:identifier>/cancel/",
        PublicRequestCancelView.as_view(),
    ),
    path("api/v1/staff/service-requests/", StaffRequestsView.as_view()),
    path(
        "api/v1/staff/service-requests/<uuid:identifier>/status/", StaffRequestStatusView.as_view()
    ),
    path("api/v1/admin/staff/sector-options/", SectorOptionsView.as_view()),
    path("api/v1/admin/staff/<uuid:identifier>/sectors/", StaffSectorsView.as_view()),
    path("api/v1/staff/production/items/", ProductionItemsView.as_view()),
    path("api/v1/staff/items/<uuid:identifier>/status/", ItemStatusView.as_view()),
    path("api/v1/public/orders/", PublicOrdersView.as_view()),
    path("api/v1/public/order-receipts/<uuid:key>/", PublicOrderReceiptView.as_view()),
    path("api/v1/public/session/", PublicSessionView.as_view()),
    path("api/v1/public/session/participants/", PublicParticipantsView.as_view()),
    path(
        "api/v1/public/session/participants/<uuid:identifier>/",
        PublicParticipantDetailView.as_view(),
    ),
    path("api/v1/staff/orders/", ManualOrderView.as_view()),
    path("api/v1/staff/tables/", StaffTablesView.as_view()),
    path("api/v1/staff/tables/<uuid:identifier>/menu/", StaffPointMenuView.as_view()),
    path("api/v1/staff/operation/", StaffOperationView.as_view()),
    path("api/v1/staff/deliveries/", StaffDeliveryItemsView.as_view()),
    path("api/v1/staff/sessions/<uuid:identifier>/orders/", StaffSessionOrdersView.as_view()),
    path("api/v1/public/menu/", PublicMenuView.as_view()),
    path("api/v1/public/categories/", PublicCategoriesView.as_view()),
    path("api/v1/public/products/<uuid:identifier>/", PublicProductView.as_view()),
    path("api/v1/public/products/<uuid:identifier>/image/", PublicProductImageView.as_view()),
    path("api/v1/public/quote/", PublicQuoteView.as_view()),
    path("api/v1/admin/products/<uuid:identifier>/image/", ProductImageView.as_view()),
    path("api/v1/admin/service-points/", PointListView.as_view()),
    path("api/v1/admin/service-points/menu-options/", PointMenuOptionsView.as_view()),
    path(
        "api/v1/admin/service-points/menu-options/<uuid:identifier>/",
        PointMenuOptionDetailView.as_view(),
    ),
    path("api/v1/admin/service-points/<uuid:identifier>/", PointDetailView.as_view()),
    path("api/v1/admin/service-points/<uuid:identifier>/url/", PointUrlView.as_view()),
    path("api/v1/admin/service-points/<uuid:identifier>/qr/", PointQrView.as_view()),
    path("api/v1/admin/service-points/<uuid:identifier>/devices/", PointDevicesView.as_view()),
    path("api/v1/admin/device-access/<uuid:identifier>/revoke/", DeviceRevokeView.as_view()),
    path("api/v1/public/access/", AccessView.as_view()),
    path("api/v1/public/context/", PublicContextView.as_view()),
    path("api/v1/platform/login/", PlatformLoginView.as_view()),
    path("api/v1/platform/me/", PlatformMeView.as_view()),
    path("api/v1/platform/logout/", PlatformLogoutView.as_view()),
    path("api/v1/platform/companies/", PlatformCompanyView.as_view()),
    path("api/v1/platform/units/", PlatformUnitView.as_view()),
    path("api/v1/staff/login/", PinLoginView.as_view()),
    path("api/v1/staff/password-login/", PasswordLoginView.as_view()),
    path("api/v1/staff/me/", StaffMeView.as_view()),
    path("api/v1/staff/units/", StaffUnitsView.as_view()),
    path("api/v1/staff/logout/", LogoutView.as_view()),
    path("api/v1/admin/staff/", StaffListView.as_view()),
    path("api/v1/admin/staff/<uuid:identifier>/", StaffDetailView.as_view()),
    path("api/v1/admin/roles/", RoleListView.as_view()),
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/csrf/", CsrfView.as_view(), name="csrf"),
]
for kind in CATALOG:
    urlpatterns.extend(
        [
            path(f"api/v1/admin/{kind}/", CatalogView.as_view(kind=kind)),
            path(f"api/v1/admin/{kind}/<uuid:identifier>/", CatalogDetailView.as_view(kind=kind)),
        ]
    )
if settings.DEBUG:
    urlpatterns.append(path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"))

handler404 = not_found
handler500 = server_error
