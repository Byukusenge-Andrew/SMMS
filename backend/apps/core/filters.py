from typing import Any

from django.db.models import Model
from django.db.models.query import QuerySet
from rest_framework.filters import BaseFilterBackend


class OwnedByUserFilterBackend(BaseFilterBackend):
    """
    Global filter that automatically restricts querysets to the authenticated user
    when the underlying model has a `user` ForeignKey field.

    Applies to list endpoints and views that go through DRF's filtering pipeline.
    """

    def filter_queryset(self, request, queryset: QuerySet, view) -> QuerySet:
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return queryset

        model: type[Model] = queryset.model
        # Only apply when the model has a `user` field
        if hasattr(model, "_meta") and any(f.name == "user" for f in model._meta.get_fields()):
            try:
                # Allow staff to bypass user filtering
                if getattr(user, "is_staff", False):
                    return queryset
                return queryset.filter(user=user)
            except Exception:
                # If filtering fails for any reason, return as-is
                return queryset
        return queryset
