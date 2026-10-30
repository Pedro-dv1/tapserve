import unicodedata

from django.db import models
from django.db.models.functions import Lower


def search_catalog(queryset, term, description=False):
    """Search the already authorized queryset, before pagination, on PostgreSQL."""
    term = " ".join(term.lower().split())
    term = "".join(c for c in unicodedata.normalize("NFD", term) if not unicodedata.combining(c))
    if not term:
        return queryset

    def folded(field):
        # ORM parameters preserve literal user input; no dynamic SQL or tenant bypass.
        return models.Func(
            Lower(field),
            models.Value("áàäâãåéèëêíìïîóòöôõúùüûçñ"),
            models.Value("aaaaaaeeeeiiiiooooouuuucn"),
            function="TRANSLATE",
            output_field=models.TextField(),
        )

    queryset = queryset.alias(_search_name=folded("name"))
    condition = models.Q(_search_name__contains=term)
    if description:
        queryset = queryset.alias(_search_description=folded("description"))
        condition |= models.Q(_search_description__contains=term)
    return (
        queryset.filter(condition)
        .alias(
            _search_rank=models.Case(
                models.When(_search_name=term, then=0),
                models.When(_search_name__startswith=term, then=1),
                default=2,
                output_field=models.IntegerField(),
            )
        )
        .order_by("_search_rank", "name", "id")
    )
