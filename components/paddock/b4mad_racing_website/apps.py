from django.apps import AppConfig


class B4madReacingWebsiteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "b4mad_racing_website"

    def ready(self):
        from . import signals  # noqa: F401 pylint: disable=unused-import,import-outside-toplevel
