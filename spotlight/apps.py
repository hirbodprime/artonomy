from django.apps import AppConfig


class SpotlightConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'spotlight'
    def ready(self):
        import spotlight.signals
