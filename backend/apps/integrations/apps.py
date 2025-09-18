from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integrations"
    verbose_name = "Integrations"

    def ready(self):
        # Lazy import admin registrations and signals to avoid side effects
        from . import admin  # noqa: F401
        from . import signals  # noqa: F401
