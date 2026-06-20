"""Base classes for tenant isolation testing."""

import pytest
from django.test import TestCase

from src.domain.models import Organization
from src.infrastructure.multitenancy.context import (
    set_current_organization, clear_current_organization
)


class TenantIsolationTestCase(TestCase):
    """Base test case for validating tenant data isolation.

    Provides utilities to set/clear context and assert isolation boundaries.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test tenants
        cls.tenant_a = Organization.objects.unfiltered.create(
            name="Test Tenant A",
            slug="test-tenant-a",
            admin_email="admin@a.test"
        )
        cls.tenant_b = Organization.objects.unfiltered.create(
            name="Test Tenant B",
            slug="test-tenant-b",
            admin_email="admin@b.test"
        )

    def set_context(self, organization):
        """Set tenant context for current test."""
        set_current_organization(organization.id)

    def clear_context(self):
        """Clear tenant context."""
        clear_current_organization()

    def tearDown(self):
        """Always clean up context after each test."""
        self.clear_context()
        super().tearDown()

    def assert_tenant_isolation(self, tenant, queryset, expected_count, msg=None):
        """Assert that queryset respects tenant context.

        Args:
            tenant: Organization to set context for
            queryset: QuerySet to evaluate
            expected_count: Expected number of results
            msg: Optional assertion message
        """
        self.set_context(tenant)
        actual = queryset.count()
        if msg is None:
            msg = (
                f"Expected {expected_count} results for {tenant.name}, "
                f"got {actual}"
            )
        self.assertEqual(actual, expected_count, msg)

    def assert_tenant_cannot_see_other_data(self, tenant_a, tenant_b, queryset_a_looks_for_b):
        """Assert that Tenant A cannot see Tenant B's data.

        Args:
            tenant_a: Context tenant
            tenant_b: Tenant whose data should be hidden
            queryset_a_looks_for_b: QuerySet searching for Tenant B data in A context
        """
        self.set_context(tenant_a)
        count = queryset_a_looks_for_b.count()
        self.assertEqual(
            count, 0,
            f"{tenant_a.name} should not see {tenant_b.name}'s data"
        )


@pytest.fixture
def tenant_a(db):
    """Pytest fixture: Tenant A."""
    return Organization.objects.unfiltered.create(
        name="Pytest Tenant A",
        slug="pytest-tenant-a",
        admin_email="admin@pytest-a.test"
    )


@pytest.fixture
def tenant_b(db):
    """Pytest fixture: Tenant B."""
    return Organization.objects.unfiltered.create(
        name="Pytest Tenant B",
        slug="pytest-tenant-b",
        admin_email="admin@pytest-b.test"
    )


@pytest.fixture
def with_tenant_context(tenant_a):
    """Pytest fixture: Context manager for tenant A."""
    from src.infrastructure.multitenancy.context import TenantContextManager

    return TenantContextManager(tenant_a.id)
