from typing import cast

from drf_spectacular.openapi import AutoSchema

from common.api import page_serializer


class CatalogSchema(AutoSchema):
    def get_operation_id(self):
        return (
            self.path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
            + "_"
            + self.method.lower()
        )

    def get_request_serializer(self):
        from apps.access.serializers import ReasonInput

        from .views import CATALOG, CatalogView

        if self.method == "DELETE":
            return ReasonInput()
        return CATALOG[cast(CatalogView, self.view).kind][1](context={"unit": None})

    def get_response_serializers(self):
        from .views import CATALOG, CatalogView

        if self.method == "DELETE":
            return {204: None}
        output = CATALOG[cast(CatalogView, self.view).kind][2]
        if self.method == "GET" and not self.path.endswith("{identifier}/"):
            return page_serializer(output)()
        return {201 if self.method == "POST" else 200: output()}
