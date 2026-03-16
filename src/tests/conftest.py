import pytest
from src.domain.models import Organization, Product, Order

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def organization(db):
    return Organization.objects.create(name="Test Org")

@pytest.fixture
def product(db, organization):
    return Product.objects.create(
        name="Laptop Pro",
        price=1000.00,
        organization=organization
    )