from django.apps import AppConfig

class DomainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.domain'
    verbose_name = 'Core Domain'

    def ready(self):
        # Importante: Importar dentro del método para evitar importaciones circulares
        import src.domain.signals