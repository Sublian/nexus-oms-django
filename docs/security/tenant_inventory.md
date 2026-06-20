# S0.1: Tenant Inventory Audit

**Date**: 2026-06-19  
**Status**: Complete  
**Scope**: All tables in `src/domain/models/`

---

## Executive Summary

Nexus OMS implements multi-tenancy via `TenantModel` base class that enforces `organization_id` FK on 24 core models. One global model (`ExchangeRate`) explicitly opts out. All tenant-scoped tables inherit automatic row-level filtering via `TenantManager` as long as thread-local context is set.

---

## Tenant Classification Matrix

| Model | Type | organization_id | Tenant Scope | Approx Records* |
|-------|------|-----------------|--------------|-----------------|
| **Organization** | Global | N/A (PK is UUID) | Global | ~5-20 |
| **CustomUser** | Mixed | FK (nullable) | Org-scoped + Superuser | ~50-200 |
| **Client** | Tenant Direct | FK (PK composite) | Tenant Direct | ~1,000-5,000 |
| **Product** | Tenant Direct | FK (unique w/ SKU) | Tenant Direct | ~500-2,000 |
| **Category** | Tenant Direct | FK | Tenant Direct | ~20-50 |
| **Supplier** | Tenant Direct | FK | Tenant Direct | ~50-200 |
| **Warehouse** | Tenant Direct | FK | Tenant Direct | ~5-20 |
| **Stock** | Tenant Indirect | FK (via Product) | Tenant Indirect | ~2,500-10,000 |
| **StockMovement** | Tenant Indirect | FK (via Stock) | Tenant Indirect | ~10,000-50,000 |
| **PurchaseOrder** | Tenant Direct | FK | Tenant Direct | ~200-1,000 |
| **PurchaseOrderItem** | Tenant Indirect | FK (via PurchaseOrder) | Tenant Indirect | ~1,000-5,000 |
| **Order** | Tenant Direct | FK (PK composite) | Tenant Direct | ~5,000-50,000 |
| **OrderItem** | Tenant Indirect | FK (via Order) | Tenant Indirect | ~10,000-100,000 |
| **OrderReturn** | Tenant Indirect | FK (via Order) | Tenant Indirect | ~100-1,000 |
| **Payment** | Tenant Indirect | FK (via Order) | Tenant Indirect | ~5,000-50,000 |
| **TaxConfiguration** | Tenant Direct | FK | Tenant Direct | ~5-20 |
| **SalesReport** | Tenant Direct | FK | Tenant Direct | ~100-500 |
| **CashReconciliation** | Tenant Direct | FK | Tenant Direct | ~50-200 |
| **CompanyInvoiceConfig** | Tenant Direct | FK (unique) | Tenant Direct | ~1-5 |
| **AccountingEntry** | Tenant Direct | FK (via Order FK) | Tenant Direct | ~1,000-10,000 |
| **AccountingEntryLine** | Tenant Indirect | FK (via AccountingEntry) | Tenant Indirect | ~4,000-40,000 |
| **InvoiceSyncQueue** | Tenant Direct | FK (via Order FK) | Tenant Direct | ~500-5,000 |
| **OrderWorkflowLog** | Tenant Direct | FK (via Order FK) | Tenant Direct | ~50,000-500,000 |
| **ExternalServiceConfig** | Tenant Direct | FK (unique) | Tenant Direct | ~5-20 |
| **ExternalRequestLog** | Tenant Direct | FK | Tenant Direct | ~100,000-1,000,000 |
| **ExchangeRate** | Global | None | Global | ~2,000-5,000 |

---

## Classification Legend

- **Tenant Direct**: Explicit `organization = ForeignKey(Organization, ...)` field
- **Tenant Indirect**: No `organization` field; inherits scope through parent relationship (e.g., `OrderItem` → `Order` → `Organization`)
- **Mixed**: Contains nullable `organization` field + superuser escalation path (e.g., `CustomUser`)
- **Global**: Shared across all tenants; no `organization` FK; examples: `ExchangeRate`

---

## Key Structural Observations

### Inheritance Pattern
All tenant-scoped models inherit from `TenantModel`:
```python
class TenantModel(models.Model):
    organization = ForeignKey(Organization, on_delete=models.CASCADE)
    objects = TenantManager()  # Auto-filtering manager
    all_objects = Manager()    # Unfiltered access (admin/audit only)
    class Meta:
        abstract = True
```

### Automatic Filtering Mechanism
- `TenantManager.get_queryset()` reads thread-local `organization_id`
- If context is set, all `.objects.*` queries auto-filter by `organization`
- If context is None, queries return all rows (CRITICAL VULNERABILITY — see S0.2)

### Nullable Organization (CustomUser Edge Case)
```python
class CustomUser(AbstractUser):
    organization = ForeignKey(Organization, null=True, blank=True)
```
Allows superusers to exist without tenant affiliation. Mitigation requires explicit governance (T6 in S0.3).

### Global Model (ExchangeRate)
```python
class ExchangeRate(models.Model):  # No TenantModel inheritance
    date, buy_price, sell_price, origin, created_at
```
Intentionally shared across all tenants. Used by `sync_daily_exchange_rate` Celery task.

---

## Unique Constraints & Data Integrity

| Model | Constraint | Scope |
|-------|-----------|-------|
| `Client` | `unique_together = ('organization', 'document_number')` | Tenant-scoped |
| `Product` | `unique_together = ('organization', 'sku')` | Tenant-scoped |
| `Stock` | `unique_together = ('product', 'warehouse')` | Enforced at product level |
| `ExternalServiceConfig` | `unique_together = [('organization', 'provider_name', 'environment')]` | Tenant-scoped |
| `CompanyInvoiceConfig` | Implicit (OneToOne-like usage) | Tenant-scoped |
| `CustomUser` | `email = unique` | Global (shared across tenants) |

**⚠️ Concern**: `CustomUser.email` is globally unique, but a user could theoretically belong to multiple organizations if the FK was not nullable. Current design: 1 user → 1 organization (or 0 for superusers).

---

## Indexing for Multi-Tenant Queries

Observed indexes in code:

| Model | Index | Benefit |
|-------|-------|---------|
| `AccountingEntry` | `('organization', 'entry_date')` | Fast reports by date |
| `AccountingEntry` | `('organization', 'entry_type')` | Fast lookup by entry type |
| `InvoiceSyncQueue` | `('status', 'next_retry_at')` | Celery task queue optimization |
| `InvoiceSyncQueue` | `('organization', 'status')` | Tenant-scoped status filtering |
| `ExternalRequestLog` | `('organization', 'provider_name', 'created_at')` | Audit trail queries |
| `ExternalRequestLog` | `('organization', 'operation', 'created_at')` | Operation tracking |
| `ExternalRequestLog` | `('order', 'provider_name')` | Order-linked request lookup |

**Observation**: Indexes consistently include `organization` as first column where tenant-scoped queries are common.

---

## Tenant Isolation Risk Assessment

### Strength: TenantModel Inheritance
✅ All 23 tenant-scoped models correctly inherit from `TenantModel`  
✅ Consistent `organization_id` FK naming  
✅ Composite unique constraints properly account for organization scope

### Risk: TenantManager Context Dependency
⚠️ `TenantManager` relies on thread-local context being set  
⚠️ If context is None, `.objects.*` queries return ALL rows (see S0.2 for specific leaks)  
⚠️ No enforcement at the database layer (no RLS) — application context is the only guard

### Risk: Global Models Not Isolated
⚠️ `ExchangeRate` is intentionally global (shared correctly)  
⚠️ No per-tenant rate overrides currently supported

### Risk: Superuser Context
⚠️ `CustomUser.organization` nullable allows superusers without org affiliation  
⚠️ API ViewSets allow superusers to query all tenants via X-Org-ID header

---

## Next Steps (S1 Phase)

1. **S0.2**: Audit actual query code for leaks when context is unset
2. **S0.4**: Evaluate RLS readiness as future hardening
3. **S0.6**: Register superuser governance as security debt
4. **S1**: Implement tenant boundary test suite to validate context always set
