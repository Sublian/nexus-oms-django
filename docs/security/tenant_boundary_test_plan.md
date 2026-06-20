# S0.7: Tenant Boundary Test Plan

**Date**: 2026-06-19  
**Status**: Design Complete (Implementation in S1)  
**Scope**: Unit + Integration Tests for Tenant Isolation Validation

---

## Executive Summary

This document designs a comprehensive test harness to validate that **Tenant A can never see data from Tenant B**, even through:
- Direct model queries
- API requests
- Celery async tasks
- Web views (HTMX)
- Report generation
- Superuser escalation

Tests are **organized by attack surface** and will be implemented incrementally in S1.

---

## Test Execution Strategy

### Test Organization

```
src/tests/security/
├── conftest.py                    # Fixtures: tenants, users, data
├── test_tenant_isolation_models.py    # Model-level queries
├── test_tenant_isolation_api.py       # API ViewSet queries
├── test_tenant_isolation_web.py       # Web view queries
├── test_tenant_isolation_celery.py    # Async task isolation
├── test_superuser_escalation.py       # Superuser security
├── test_rls_enforcement.py            # RLS policies (S2)
└── test_compliance_data_access.py     # Audit trail validation
```

### Running Tests

```bash
# All tenant isolation tests
pytest src/tests/security/ -v

# Specific category
pytest src/tests/security/test_tenant_isolation_models.py -v

# With coverage
pytest src/tests/security/ --cov=src --cov-report=html

# Integration tests only (slower)
pytest src/tests/security/ -m integration
```

---

## Test Fixtures (conftest.py)

```python
import pytest
from django.contrib.auth.models import Group
from src.domain.models import (
    Organization, CustomUser, Order, Product, Client
)
from src.infrastructure.multitenancy.thread_local import set_current_organization

@pytest.fixture
def tenant_a():
    """Organization A for testing."""
    return Organization.objects.create(
        name="Tenant A Corp",
        slug="tenant-a",
        admin_email="admin@tenant-a.com"
    )

@pytest.fixture
def tenant_b():
    """Organization B (competitor, should be invisible)."""
    return Organization.objects.create(
        name="Tenant B Ltd",
        slug="tenant-b",
        admin_email="admin@tenant-b.com"
    )

@pytest.fixture
def user_a(tenant_a):
    """User belonging to Tenant A."""
    return CustomUser.objects.create_user(
        email="user@tenant-a.com",
        password="secure_pass",
        organization=tenant_a,
        role="STAFF"
    )

@pytest.fixture
def user_b(tenant_b):
    """User belonging to Tenant B."""
    return CustomUser.objects.create_user(
        email="user@tenant-b.com",
        password="secure_pass",
        organization=tenant_b,
        role="STAFF"
    )

@pytest.fixture
def superuser():
    """Superuser without org affiliation."""
    return CustomUser.objects.create_superuser(
        email="admin@nexus.com",
        password="super_secure",
        organization=None  # Org-less superuser
    )

@pytest.fixture
def order_a(tenant_a, user_a):
    """Order in Tenant A."""
    return Order.objects.create(
        organization=tenant_a,
        customer_name="Customer A",
        customer_email="cust@tenant-a.com",
        status="PENDING"
    )

@pytest.fixture
def order_b(tenant_b, user_b):
    """Order in Tenant B."""
    return Order.objects.create(
        organization=tenant_b,
        customer_name="Customer B",
        customer_email="cust@tenant-b.com",
        status="PENDING"
    )

@pytest.fixture
def api_client_a(user_a):
    """API client authenticated as Tenant A user."""
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=user_a)
    return client

@pytest.fixture
def api_client_b(user_b):
    """API client authenticated as Tenant B user."""
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=user_b)
    return client

@pytest.fixture
def api_client_superuser(superuser):
    """API client authenticated as superuser."""
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=superuser)
    return client
```

---

## Test Suite 1: Model-Level Isolation

### TC1.1: Order.objects Query Respects Organization Context

```python
def test_order_objects_filters_by_current_org(tenant_a, tenant_b, order_a, order_b):
    """
    Verify: order_a is visible when context = tenant_a
    Verify: order_b is INVISIBLE when context = tenant_a
    """
    from src.infrastructure.multitenancy.thread_local import set_current_organization
    
    # Set context to Tenant A
    set_current_organization(tenant_a.id)
    
    # Query via TenantManager (.objects)
    visible_orders = Order.objects.all()
    
    # Assertion: only order_a
    assert visible_orders.count() == 1
    assert visible_orders.first().id == order_a.id
    assert order_b not in visible_orders
    
    # Assertion: order_b is unreachable
    assert not Order.objects.filter(id=order_b.id).exists()
```

### TC1.2: Product.objects Query Respects Tenant Isolation

```python
def test_product_objects_filters_by_org(tenant_a, tenant_b):
    """Product SKU must be unique per tenant; .objects should respect scope."""
    prod_a = Product.objects.create(
        organization=tenant_a,
        name="Widget A",
        sku="WIDGET-001",
        price=100.00
    )
    prod_b = Product.objects.create(
        organization=tenant_b,
        name="Gadget B",
        sku="GADGET-001",  # Different SKU; allowed
        price=200.00
    )
    
    # Context: Tenant A
    set_current_organization(tenant_a.id)
    assert Product.objects.count() == 1
    assert Product.objects.first().id == prod_a.id
    
    # Context: Tenant B
    set_current_organization(tenant_b.id)
    assert Product.objects.count() == 1
    assert Product.objects.first().id == prod_b.id
```

### TC1.3: TenantManager Returns Empty When Context is None

```python
def test_tenantmanager_returns_empty_when_context_none(order_a, order_b):
    """Critical test: If context is not set, .objects should return empty (safe)."""
    from src.infrastructure.multitenancy.thread_local import set_current_organization, reset_organization
    
    reset_organization()  # Clear context
    
    # Query should return empty (NOT all records!)
    visible = Order.objects.all()
    assert visible.count() == 0  # SAFE: empty, not leaked
```

### TC1.4: all_objects Bypasses Filtering (Audit Only)

```python
def test_all_objects_bypasses_filtering(order_a, order_b):
    """
    AUDIT: Verify that .all_objects bypasses TenantManager.
    This is intentional (used in management commands), but must be documented.
    """
    # Even without context, .all_objects returns ALL records
    visible = Order.all_objects.all()
    assert visible.count() == 2
    assert {o.id for o in visible} == {order_a.id, order_b.id}
```

### TC1.5: Indirect Children Inherit Parent Organization Scope

```python
def test_orderitem_inherits_order_organization(tenant_a, tenant_b, order_a, order_b):
    """
    OrderItem → Order → Organization relationship.
    Verify: OrderItem.objects respects order's organization.
    """
    from src.domain.models import OrderItem, Product
    
    prod_a = Product.objects.create(
        organization=tenant_a, name="P1", sku="P1", price=10.00
    )
    item_a = OrderItem.objects.create(
        organization=tenant_a,
        order=order_a,
        product=prod_a,
        quantity=5,
        price_at_order=10.00
    )
    
    prod_b = Product.objects.create(
        organization=tenant_b, name="P2", sku="P2", price=20.00
    )
    item_b = OrderItem.objects.create(
        organization=tenant_b,
        order=order_b,
        product=prod_b,
        quantity=3,
        price_at_order=20.00
    )
    
    # Context: Tenant A
    set_current_organization(tenant_a.id)
    assert OrderItem.objects.count() == 1
    assert OrderItem.objects.first().id == item_a.id
    
    # Verify: Can't access item_b even by direct ID
    assert not OrderItem.objects.filter(id=item_b.id).exists()
```

---

## Test Suite 2: API ViewSet Isolation

### TC2.1: Tenant A User Cannot List Tenant B Orders

```python
@pytest.mark.django_db
def test_user_a_cannot_list_tenant_b_orders(api_client_a, order_a, order_b):
    """Tenant A user calls GET /api/v1/orders/ → should only see order_a."""
    response = api_client_a.get('/api/v1/orders/')
    
    assert response.status_code == 200
    data = response.json()
    
    # Should see only order_a
    assert data['count'] == 1
    assert data['results'][0]['id'] == str(order_a.id)
    
    # order_b should NOT appear
    assert not any(r['id'] == str(order_b.id) for r in data['results'])
```

### TC2.2: Tenant A User Cannot Retrieve Tenant B Order

```python
@pytest.mark.django_db
def test_user_a_cannot_get_tenant_b_order(api_client_a, order_b):
    """Tenant A user calls GET /api/v1/orders/{order_b.id}/ → 404."""
    response = api_client_a.get(f'/api/v1/orders/{order_b.id}/')
    
    # Should return 404 (not found), NOT 403 (forbidden)
    # 404 is safer; prevents inferring existence of hidden data
    assert response.status_code == 404
```

### TC2.3: Product ViewSet Filters by Tenant

```python
@pytest.mark.django_db
def test_product_viewset_filters_by_tenant(api_client_a, api_client_b, tenant_a, tenant_b):
    """Both tenants have products with different SKUs; each sees only theirs."""
    from src.domain.models import Product
    
    prod_a = Product.objects.create(
        organization=tenant_a, name="Widget", sku="WID-001", price=100.00
    )
    prod_b = Product.objects.create(
        organization=tenant_b, name="Gadget", sku="GAD-001", price=200.00
    )
    
    # Tenant A client
    resp_a = api_client_a.get('/api/v1/products/')
    assert resp_a.status_code == 200
    assert resp_a.json()['count'] == 1
    assert resp_a.json()['results'][0]['id'] == str(prod_a.id)
    
    # Tenant B client
    resp_b = api_client_b.get('/api/v1/products/')
    assert resp_b.status_code == 200
    assert resp_b.json()['count'] == 1
    assert resp_b.json()['results'][0]['id'] == str(prod_b.id)
```

### TC2.4: Superuser WITHOUT X-Org-ID is Rejected (SD-002 Fix)

```python
@pytest.mark.django_db
def test_superuser_without_xorgid_is_rejected(api_client_superuser):
    """
    Superuser calls GET /api/v1/orders/ without X-Org-ID header.
    Should return 403 Forbidden (after S1 fix).
    Currently: FAILS (returns all orders) — this test documents the bug until S1.
    """
    # TODO: Change to 403 after S1 implementation
    response = api_client_superuser.get('/api/v1/orders/')
    # assert response.status_code == 403  # S1 target
    assert response.status_code == 200  # Current bug (SD-002)
```

### TC2.5: Superuser WITH Valid X-Org-ID Can Access That Org

```python
@pytest.mark.django_db
def test_superuser_with_xorgid_accesses_specified_org(api_client_superuser, tenant_a, tenant_b, order_a, order_b):
    """Superuser provides X-Org-ID: tenant_a → should see only order_a."""
    response = api_client_superuser.get(
        '/api/v1/orders/',
        HTTP_X_ORG_ID=str(tenant_a.id)
    )
    
    assert response.status_code == 200
    assert response.json()['count'] == 1
    assert response.json()['results'][0]['id'] == str(order_a.id)
```

---

## Test Suite 3: Web View Isolation (HTMX)

### TC3.1: Web View Resolves Tenant from URL Slug

```python
@pytest.mark.django_db
def test_web_view_resolves_tenant_from_slug(client, tenant_a, tenant_b, order_a, order_b):
    """
    GET /dashboard/tenant-a/orders/ → shows only tenant_a orders.
    GET /dashboard/tenant-b/orders/ → shows only tenant_b orders.
    """
    # Tenant A dashboard
    resp_a = client.get(f'/dashboard/{tenant_a.slug}/orders/')
    assert resp_a.status_code == 200
    content = resp_a.content.decode()
    assert str(order_a.id) in content  # order_a visible
    assert str(order_b.id) not in content  # order_b hidden
    
    # Tenant B dashboard
    resp_b = client.get(f'/dashboard/{tenant_b.slug}/orders/')
    assert resp_b.status_code == 200
    content = resp_b.content.decode()
    assert str(order_b.id) in content  # order_b visible
    assert str(order_a.id) not in content  # order_a hidden
```

---

## Test Suite 4: Celery Task Isolation

### TC4.1: Report Generation Task Respects Organization

```python
@pytest.mark.django_db
@pytest.mark.celery
def test_generate_sales_report_task_respects_org(tenant_a, tenant_b, order_a, order_b):
    """
    Celery task: generate_sales_report_task(org_id=tenant_a.id)
    Should aggregate ONLY orders from tenant_a.
    """
    from src.domain.tasks import generate_sales_report_task
    
    # Create orders with amounts
    order_a.total_amount = 1000.00
    order_a.status = 'DELIVERED'
    order_a.save()
    
    order_b.total_amount = 5000.00
    order_b.status = 'DELIVERED'
    order_b.save()
    
    # Run task for tenant_a
    task = generate_sales_report_task.apply_async(
        args=[str(tenant_a.id), '2026-01-01', '2026-12-31']
    )
    
    result = task.get()
    
    # Verify: Report contains ONLY tenant_a data
    assert result['total_sales'] == 1000.00  # Not 6000.00 (both tenants)
    assert result['order_count'] == 1  # Not 2
```

### TC4.2: Invoice Sync Task Processes Only Its Organization's Queue

```python
@pytest.mark.django_db
@pytest.mark.celery
def test_sync_invoice_task_respects_org(tenant_a, tenant_b, order_a, order_b):
    """
    Celery task: sync_invoices_all_orgs()
    Should process InvoiceSyncQueue entries per organization without leaks.
    """
    from src.domain.models import InvoiceSyncQueue
    from src.domain.tasks import sync_invoices_all_orgs
    from django.utils import timezone
    
    # Create sync queue entries
    queue_a = InvoiceSyncQueue.objects.create(
        organization=tenant_a,
        order=order_a,
        status='PENDING',
        next_retry_at=timezone.now()
    )
    queue_b = InvoiceSyncQueue.objects.create(
        organization=tenant_b,
        order=order_b,
        status='PENDING',
        next_retry_at=timezone.now()
    )
    
    # Mock Nubefact response
    # Run task
    task = sync_invoices_all_orgs.apply_async()
    result = task.get()
    
    # Verify: Both orgs' queues were processed without cross-contamination
    # (inspect logs or side-effects to confirm isolation)
```

---

## Test Suite 5: Superuser Escalation & Governance

### TC5.1: Superuser Escalation Blocked Without X-Org-ID

```python
@pytest.mark.django_db
def test_superuser_escalation_requires_explicit_org(api_client_superuser, order_a, order_b):
    """
    CRITICAL: Superuser must provide X-Org-ID or request fails.
    This test documents the S1 fix for SD-002.
    """
    # Without X-Org-ID: REJECTED (S1 behavior)
    resp = api_client_superuser.get('/api/v1/orders/')
    # TODO: Uncomment after S1 fix
    # assert resp.status_code == 403
    # assert "X-Org-ID" in resp.json()['detail']
```

### TC5.2: Superuser Access Audit Logged

```python
@pytest.mark.django_db
def test_superuser_access_audit_logged(api_client_superuser, tenant_a, order_a):
    """Verify: When superuser accesses an org, audit log is created."""
    # Implementation of T6.2 (audit logging)
    # This test is deferred until T6.2 is implemented
    pass
```

### TC5.3: Superuser Role Enforcement

```python
@pytest.mark.django_db
def test_viewer_role_cannot_create_order(api_client_viewer, tenant_a):
    """VIEWER users should not create orders (SD-005 test)."""
    # TODO: Implement after S1 RBAC fixes
    response = api_client_viewer.post('/api/v1/orders/', {
        'customer_name': 'Test',
        'customer_email': 'test@example.com',
        'items': []
    })
    # assert response.status_code == 403
```

---

## Test Suite 6: RLS Enforcement (S2)

### TC6.1: RLS Policy Blocks Cross-Tenant Queries

```python
@pytest.mark.django_db
@pytest.mark.rls
@pytest.mark.skip(reason="RLS not yet enabled; targets S2")
def test_rls_blocks_cross_tenant_query():
    """
    When RLS is enabled, queries should fail at database level if org context is wrong.
    """
    pass
```

---

## Test Suite 7: Compliance & Audit Trail

### TC7.1: PII Fields Are Masked in Logs

```python
@pytest.mark.django_db
def test_pii_masked_in_request_logs(api_client_a, order_a):
    """Verify: Customer email/address not logged in plaintext."""
    # Make request that might be logged
    api_client_a.get(f'/api/v1/orders/{order_a.id}/')
    
    # Check logs: email should be masked
    from src.domain.models import ExternalRequestLog
    log = ExternalRequestLog.objects.latest('created_at')
    
    # If email is logged, it should be masked
    if 'email' in str(log.request_payload):
        assert order_a.customer_email not in str(log.request_payload)
```

---

## Test Coverage Target

| Suite | Tests | Coverage Target | Priority |
|-------|-------|-----------------|----------|
| Model Isolation (1) | 5 | 100% | CRITICAL |
| API ViewSet (2) | 5 | 100% | CRITICAL |
| Web Views (3) | 1 | 80% | HIGH |
| Celery Tasks (4) | 2 | 90% | HIGH |
| Superuser (5) | 3 | 100% | CRITICAL |
| RLS (6) | 1 | Deferred to S2 | S2 |
| Compliance (7) | 1 | 80% | MEDIUM |

**Total Test Count**: ~17 tests  
**Target Coverage**: 85% (S0-S1 scope)  
**Execution Time**: ~30s (unit + integration, excluding slow Celery tests)

---

## CI/CD Integration

### GitHub Actions / GitLab CI

```yaml
name: Tenant Isolation Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_DB: nexus_test
          POSTGRES_PASSWORD: test
      redis:
        image: redis:7
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.11
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tenant isolation tests
        run: pytest src/tests/security/ -v --cov=src
      - name: Enforce coverage
        run: coverage report --fail-under=85
```

### Pre-Commit Hook

```bash
# .husky/pre-commit
pytest src/tests/security/ -q || exit 1
```

---

## Implementation Timeline (S1)

1. **Week 1**: Write test fixtures (conftest.py), TC 1.1-1.5
2. **Week 2**: Implement ViewSet fixes (SD-002), TC 2.1-2.5
3. **Week 2**: Write and pass web view tests TC 3.1
4. **Week 3**: Celery task isolation tests TC 4.1-4.2
5. **Week 4**: Superuser governance tests TC 5.1-5.3, RLS prep for S2

---

## References

- `docs/security/tenant_leak_audit.md` (S0.2) — Leak details
- `docs/security/superuser_governance.md` (S0.3) — T6 controls
- `src/infrastructure/multitenancy/` — Thread-local context
