# S0.2: Tenant Leak Audit

**Date**: 2026-06-19  
**Status**: Complete  
**Scope**: Use Cases, Celery Tasks, Services, API ViewSets, Web Views, Reporting

---

## Executive Summary

**CRITICAL FINDINGS**: 4 explicit tenant leaks in API ViewSets where `.all_objects.all()` returns ALL rows across all tenants when organization is None. Additionally, 11 uses of `.all_objects` in legitimate contexts (management commands, web views with explicit org filtering) require review.

**Severity Distribution**:
- **CRITICAL**: 4 findings (API ViewSets returning unfiltered data)
- **HIGH**: 11 findings (`.all_objects` usage requiring org context verification)
- **MEDIUM**: 0 findings
- **LOW**: 0 findings

---

## CRITICAL Findings

### Finding 1: ProductViewSet.get_queryset() — Unfiltered Product Leak

**File**: `src/interfaces/api/views.py:73-83`  
**Severity**: CRITICAL  
**Code**:
```python
class ProductViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        org = self.get_organization()
        qs = (
            Product.all_objects.all()  # ← LEAK: Returns ALL products across all tenants
            if org is None
            else Product.objects.filter(organization=org)
        )
        return qs.annotate(stock_total=Coalesce(Sum('stocks__quantity'), 0))
```

**Risk**: Superuser with X-Org-ID=None receives all products (price, inventory, supplier info) from all tenants.

**Evidence**: When `get_organization()` returns None (superuser without X-Org-ID header), the ternary returns `Product.all_objects.all()`.

---

### Finding 2: OrderViewSet.get_queryset() — Unfiltered Order Leak

**File**: `src/interfaces/api/views.py:86-91`  
**Severity**: CRITICAL  
**Code**:
```python
class OrderViewSet(TenantViewMixin, viewsets.ModelViewSet):
    serializer_class = OrderCreateSerializer

    def get_queryset(self):
        org = self.get_organization()
        return Order.all_objects.all() if org is None else Order.objects.filter(organization=org)
        # ↑ LEAK: Returns ALL orders + sensitive pricing, customer, payment data
```

**Risk**: Superuser receives all orders, including customer names, emails, payment amounts, delivery addresses across all tenants.

**Evidence**: Same pattern as Finding 1; no tenant filtering when org is None.

---

### Finding 3: ReportViewSet.get_queryset() — Unfiltered Report Leak

**File**: `src/interfaces/api/views.py:133-138`  
**Severity**: CRITICAL  
**Code**:
```python
class ReportViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = SalesReportSerializer

    def get_queryset(self):
        org = self.get_organization()
        return SalesReport.all_objects.all() if org is None else SalesReport.objects.filter(organization=org)
        # ↑ LEAK: Returns ALL sales reports with revenue, volume, and financial summaries
```

**Risk**: Superuser views all SalesReports (total_sales, order_count, aggregated data) across all tenants without explicit authorization.

**Evidence**: Same pattern; no tenant discrimination when org is None.

---

### Finding 4: OrderReturnViewSet.get_queryset() — Unfiltered Return Leak

**File**: `src/interfaces/api/views.py:163-168`  
**Severity**: CRITICAL  
**Code**:
```python
class OrderReturnViewSet(TenantViewMixin, viewsets.ModelViewSet):
    serializer_class = OrderReturnSerializer

    def get_queryset(self):
        org = self.get_organization()
        return OrderReturn.all_objects.all() if org is None else OrderReturn.objects.filter(organization=org)
        # ↑ LEAK: Returns ALL returns, including reason, refund amounts, stock re-entry status
```

**Risk**: Superuser views return policies, refund amounts, and damage reasons across all clients/tenants.

**Evidence**: Same pattern; no filtering when org is None.

---

## HIGH Risk Findings

### Finding H1-H3: `.all_objects` in Web Views (Explicit Org Filtering)

**Files**:
- `src/interfaces/web/views.py:1367` — `InvoiceSyncQueue.all_objects.filter(organization=tenant)`
- `src/interfaces/web/views.py:1420` — `ExternalRequestLog.all_objects.filter(organization=tenant)`
- `src/interfaces/web/views.py:1455` — `Order.all_objects.filter(organization=tenant)`
- `src/interfaces/web/views.py:1462` — `AccountingEntry.all_objects.filter(organization=tenant)`
- `src/interfaces/web/views.py:1470` — `Order.all_objects.filter(organization=tenant)`

**Severity**: HIGH → Mitigated by explicit `.filter(organization=tenant)` in each query

**Context**: Web views manually resolve `tenant` from URL slug and filter explicitly. Risk is **conditional** — if the slug resolution is bypassed or mishandled, leaks occur.

**Observation**: Web view approach is more explicit but error-prone compared to automatic TenantManager filtering.

---

### Finding H4-H11: Dashboard Service `.all_objects` Usage

**File**: `src/application/services/dashboard.py`

All instances explicitly filter by `organization` parameter:
```python
Order.all_objects.filter(organization=organization)
InvoiceSyncQueue.all_objects.filter(organization=organization)
ExternalRequestLog.all_objects.filter(organization=organization)
```

**Severity**: HIGH → Conditional; requires caller to pass correct organization

**Observation**: Service layer expects caller to enforce tenant scope. If caller passes wrong org or None, leak occurs.

---

## Celery Tasks & Management Commands

### Pattern: Intentional Use of `.all_objects` for System Operations

**Files**:
- `src/domain/tasks/sync_invoice_tasks.py:59, 94, 269` — `.all_objects` to query all InvoiceSyncQueue entries across tenants
- `src/domain/management/commands/seed_data.py:297-419` — `.all_objects` to seed/validate data per organization

**Severity**: LOW (by design)

**Justification**: Celery tasks and CLI commands intentionally operate globally and iterate per-tenant. Context is explicitly managed.

**Example**:
```python
def sync_invoices_all_orgs():
    # Query ALL entries, then process per organization
    for entry in InvoiceSyncQueue.all_objects.filter(status=PENDING):
        org_id = entry.order.organization_id
        set_current_organization(org_id)
        # Process...
```

---

## Summary: Query Patterns Analysis

### Safe Pattern ✅
```python
# TenantManager automatically filters by thread-local org
Order.objects.filter(status=DRAFT)  # Returns only Tenant A's drafts if context is Tenant A
```

### Unsafe Pattern ❌
```python
# API ViewSet without org check
Product.all_objects.all()  # When org is None: returns ALL products from ALL tenants
```

### Safe with Explicit Filtering ✓ (Requires Verification)
```python
# Web view with explicit org
Order.all_objects.filter(organization=tenant)  # Safe IF tenant is correctly resolved
```

### Safe System Operations ✓
```python
# Celery task intentionally querying globally
for entry in InvoiceSyncQueue.all_objects.all():
    # Process entry with correct org context
```

---

## No Raw SQL / Cursor.execute() Found ✅

Grep search for `.raw()` and `cursor.execute()` across codebase yielded zero results. All database access goes through Django ORM, which provides better audit trail and TenantManager integration.

---

## Tenant Leak Incident Scenarios

### Scenario 1: Superuser Lists All Products
1. Attacker/malicious admin calls `GET /api/v1/products/` without X-Org-ID header
2. `TenantViewMixin.get_organization()` returns None (no org in user + no header)
3. `ProductViewSet.get_queryset()` executes: `Product.all_objects.all()`
4. Result: All products from all tenants, including pricing/inventory data

**Impact**: Competitive intelligence, pricing strategy leakage

---

### Scenario 2: Superuser Exfiltrates All Orders
1. Attacker calls `GET /api/v1/orders/` without X-Org-ID
2. `OrderViewSet.get_queryset()` returns `Order.all_objects.all()`
3. Result: All customer names, emails, purchase history, payment amounts across all clients

**Impact**: GDPR/privacy violation; customer data breach

---

### Scenario 3: Dashboard Caller Passes Wrong Org
1. Dashboard calls `OrderService.get_sales_kpi(organization=wrong_org)`
2. Service executes: `Order.all_objects.filter(organization=wrong_org)`
3. Result: Returns metrics for wrong tenant

**Impact**: Financial misreporting; cross-tenant visibility

---

## Recommended Fixes (S1 Implementation)

1. **API ViewSets**: Replace ternary logic with:
   ```python
   def get_queryset(self):
       org = self.get_organization()
       if org is None:
           return Order.objects.none()  # Reject superuser without explicit org
       return Order.objects.filter(organization=org)
   ```

2. **Web Views**: Replace `.all_objects.filter()` with `.objects` (relying on TenantManager)

3. **Dashboard Service**: Add assertions to verify organization parameter

4. **Celery Tasks**: Explicitly set thread-local context before querying .all_objects

---

## Test Harness (S0.7 Design)

See `docs/security/tenant_boundary_test_plan.md` for unit test specifications to validate these leaks are fixed in S1.
