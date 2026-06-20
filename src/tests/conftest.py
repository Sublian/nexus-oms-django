import pytest
from src.domain.models import Organization, Product, Order

@pytest.fixture(autouse=True)
def eager_celery(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

@pytest.fixture(autouse=True)
def clear_tenant_context():
    """Clear tenant context after each test to avoid cross-contamination."""
    from src.infrastructure.multitenancy.context import clear_current_organization
    yield
    clear_current_organization()

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def admin_user(db, organization):
    from src.domain.models.users import CustomUser, UserRole
    user = CustomUser(
        email='admin@test.com',
        organization=organization,
        role=UserRole.ADMIN,
        first_name='Admin',
        last_name='Test',
    )
    user.set_password('testpass123')
    user.save()
    return user

@pytest.fixture
def auth_api_client(api_client, admin_user, organization):
    """APIClient autenticado; tenant resuelto desde user.organization."""
    api_client.force_authenticate(user=admin_user)
    # Context is set by organization fixture
    return api_client

@pytest.fixture
def logged_in_client(client, admin_user):
    """Django test client con sesión activa como admin_user."""
    client.force_login(admin_user)
    return client

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
    """Create test organization and set as current tenant context."""
    from src.infrastructure.multitenancy.context import set_current_organization
    org = org_factory("Main Tenant")
    set_current_organization(org.id)
    return org

@pytest.fixture
def product(db, organization):
    return Product.objects.create(
        name="Laptop Pro",
        price=1000.00,
        organization=organization
    )

@pytest.fixture
def warehouse(organization):
    from src.domain.models import Warehouse
    return Warehouse.objects.create(
        name="Bodega Central",
        organization=organization
    )

@pytest.fixture
def supplier(organization):
    from src.domain.models import Supplier
    return Supplier.objects.create(
        name="Proveedor Tech",
        organization=organization
    )

@pytest.fixture(autouse=True)
def mock_migo_token(settings):
    settings.MIGO_API_TOKEN = "test_token_123"

@pytest.fixture
def exchange_rate_fixture(db):
    """Pre-populate ExchangeRate for today to prevent HTTP calls to APIMigo during tests.

    This fixture blocks ExchangeService.get_current_rate() from attempting network calls.
    Only auto-used in web interface tests, not in service unit tests.
    """
    from datetime import date
    from decimal import Decimal
    from src.domain.models import ExchangeRate

    # Seed today's exchange rate (prevents HTTP leak to api.migo.pe)
    ExchangeRate.objects.get_or_create(
        date=date.today(),
        defaults={
            'buy_price': Decimal('3.75'),
            'sell_price': Decimal('3.80'),
            'origin': 'test'
        }
    )

@pytest.fixture
def tenant_a(db):
    """Pytest fixture: Tenant A for security tests."""
    from src.infrastructure.multitenancy.context import set_current_organization
    tenant = Organization.objects.create(
        name="Pytest Tenant A",
        slug="pytest-tenant-a",
        admin_email="admin@pytest-a.test"
    )
    set_current_organization(tenant.id)
    return tenant

@pytest.fixture
def tenant_b(db):
    """Pytest fixture: Tenant B for security tests."""
    from src.infrastructure.multitenancy.context import set_current_organization
    tenant = Organization.objects.create(
        name="Pytest Tenant B",
        slug="pytest-tenant-b",
        admin_email="admin@pytest-b.test"
    )
    set_current_organization(tenant.id)
    return tenant
