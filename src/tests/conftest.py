import pytest
from src.domain.models import Organization, Product, Order

# Añade esto arriba de tus tests de tareas si no está en settings de test
@pytest.fixture(autouse=True)
def eager_celery(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    
@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def org_factory(db):
    """Factory para crear múltiples organizaciones sin choque de slugs."""
    def _make_org(name):
        return Organization.objects.create(
            name=name, 
            slug=name.lower().replace(" ", "-") # Aseguramos slug único
        )
    return _make_org

@pytest.fixture
def organization(org_factory):
    return org_factory("Main Tenant")

@pytest.fixture
def product(db, organization):
    return Product.objects.create(
        name="Laptop Pro",
        price=1000.00,
        organization=organization
    )