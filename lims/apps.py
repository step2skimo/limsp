from django.apps import AppConfig


class LimsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lims'

    def ready(self):
        import lims.signals
