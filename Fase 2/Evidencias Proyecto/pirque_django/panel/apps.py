from django.apps import AppConfig


class PanelConfig(AppConfig):
    name = "panel"

    def ready(self):
        from . import checks  # noqa: F401  (registra los avisos de seguridad para producción)
