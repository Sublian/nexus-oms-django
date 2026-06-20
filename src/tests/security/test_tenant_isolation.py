"""Test suite for tenant data isolation (cross-tenant boundary validation)."""

import pytest
from django.test import TestCase

from src.domain.models import Order, Product
from src.tests.security.base import TenantIsolationTestCase


class TestTenantManagerAutoFiltering(TenantIsolationTestCase):
    """Test TenantManager automatic filtering by context."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create products per tenant
        cls.product_a = Product.objects.create(
            organization=cls.tenant_a,
            name="Product A",
            sku="SKU-A",
            price=100.00
        )
        cls.product_b = Product.objects.create(
            organization=cls.tenant_b,
            name="Product B",
            sku="SKU-B",
            price=200.00
        )

        # Create orders per tenant
        cls.order_a = Order.objects.create(
            organization=cls.tenant_a,
            customer_name="Customer A",
            customer_email="a@tenant-a.test"
        )
        cls.order_b = Order.objects.create(
            organization=cls.tenant_b,
            customer_name="Customer B",
            customer_email="b@tenant-b.test"
        )

    def test_product_queryset_respects_context_tenant_a(self):
        """Tenant A context: Product.objects should only see Tenant A products."""
        self.set_context(self.tenant_a)

        products = Product.objects.all()

        self.assertEqual(products.count(), 1, "Tenant A should see only 1 product")
        self.assertEqual(
            products.first().id, self.product_a.id,
            "Tenant A should see only its own product"
        )

    def test_product_queryset_respects_context_tenant_b(self):
        """Tenant B context: Product.objects should only see Tenant B products."""
        self.set_context(self.tenant_b)

        products = Product.objects.all()

        self.assertEqual(products.count(), 1, "Tenant B should see only 1 product")
        self.assertEqual(
            products.first().id, self.product_b.id,
            "Tenant B should see only its own product"
        )

    def test_order_queryset_respects_context(self):
        """Order isolation: each tenant sees only their orders."""
        self.set_context(self.tenant_a)
        orders_a = Order.objects.all()
        self.assertEqual(orders_a.count(), 1)
        self.assertEqual(orders_a.first().id, self.order_a.id)

        self.set_context(self.tenant_b)
        orders_b = Order.objects.all()
        self.assertEqual(orders_b.count(), 1)
        self.assertEqual(orders_b.first().id, self.order_b.id)

    def test_tenant_a_cannot_access_tenant_b_order_by_id(self):
        """Tenant A with context cannot find Tenant B's order even by ID."""
        self.set_context(self.tenant_a)

        # Try to access Tenant B's order directly by ID
        found = Order.objects.filter(id=self.order_b.id)

        self.assertEqual(found.count(), 0, "Tenant A should not find Tenant B's order")

    def test_tenant_b_cannot_access_tenant_a_order_by_id(self):
        """Tenant B with context cannot find Tenant A's order even by ID."""
        self.set_context(self.tenant_b)

        found = Order.objects.filter(id=self.order_a.id)

        self.assertEqual(found.count(), 0, "Tenant B should not find Tenant A's order")

    def test_no_context_returns_empty_queryset(self):
        """No context set: .objects returns empty queryset (fail-safe)."""
        self.clear_context()

        orders = Order.objects.all()
        products = Product.objects.all()

        self.assertEqual(orders.count(), 0, "No context: orders should be empty")
        self.assertEqual(products.count(), 0, "No context: products should be empty")

    def test_unfiltered_manager_returns_all_records(self):
        """unfiltered manager bypasses context and returns all records."""
        self.clear_context()

        all_orders = Order.unfiltered.all()
        all_products = Product.unfiltered.all()

        self.assertEqual(all_orders.count(), 2, "unfiltered should return both orders")
        self.assertEqual(all_products.count(), 2, "unfiltered should return both products")

    def test_all_objects_backward_compat_returns_all(self):
        """all_objects (backward compat) bypasses context."""
        self.clear_context()

        all_orders = Order.all_objects.all()

        self.assertEqual(all_orders.count(), 2, "all_objects should return both orders")


@pytest.mark.django_db
class TestCrossTenantBoundaryPytest:
    """Pytest-style tests for cross-tenant isolation."""

    def test_tenant_context_isolation_orders(self, tenant_a, tenant_b):
        """Orders: Tenant A sees only Tenant A's orders."""
        from src.infrastructure.multitenancy.context import set_current_organization

        # Create orders
        order_a = Order.objects.create(
            organization=tenant_a,
            customer_name="Customer A",
            customer_email="a@test.com"
        )
        order_b = Order.objects.create(
            organization=tenant_b,
            customer_name="Customer B",
            customer_email="b@test.com"
        )

        # Tenant A context
        set_current_organization(tenant_a.id)
        assert Order.objects.count() == 1
        assert Order.objects.first().id == order_a.id

        # Tenant B context
        set_current_organization(tenant_b.id)
        assert Order.objects.count() == 1
        assert Order.objects.first().id == order_b.id

    def test_tenant_context_isolation_products(self, tenant_a, tenant_b):
        """Products: Tenant A sees only Tenant A's products."""
        from src.infrastructure.multitenancy.context import set_current_organization

        prod_a = Product.objects.create(
            organization=tenant_a,
            name="Product A",
            sku="A1",
            price=100.00
        )
        prod_b = Product.objects.create(
            organization=tenant_b,
            name="Product B",
            sku="B1",
            price=200.00
        )

        set_current_organization(tenant_a.id)
        assert Product.objects.count() == 1
        assert Product.objects.first().id == prod_a.id

        set_current_organization(tenant_b.id)
        assert Product.objects.count() == 1
        assert Product.objects.first().id == prod_b.id

    def test_no_context_returns_empty(self, tenant_a):
        """No context: queries return empty queryset."""
        from src.infrastructure.multitenancy.context import clear_current_organization

        Order.objects.create(
            organization=tenant_a,
            customer_name="Test",
            customer_email="test@test.com"
        )

        clear_current_organization()
        assert Order.objects.count() == 0

    def test_unfiltered_bypasses_context(self, tenant_a, tenant_b):
        """unfiltered manager ignores context."""
        from src.infrastructure.multitenancy.context import (
            set_current_organization, clear_current_organization
        )

        Order.objects.create(
            organization=tenant_a,
            customer_name="A",
            customer_email="a@test.com"
        )
        Order.objects.create(
            organization=tenant_b,
            customer_name="B",
            customer_email="b@test.com"
        )

        # Any context or no context
        clear_current_organization()
        assert Order.unfiltered.count() == 2
        assert Order.all_objects.count() == 2
