# S0.4: RLS Readiness Assessment

**Date**: 2026-06-19  
**Status**: Complete  
**Scope**: PostgreSQL Row-Level Security (RLS) Readiness for All Tenant-Scoped Tables

---

## Executive Summary

Nexus OMS is **architecturally ready** for PostgreSQL RLS hardening but does **not currently enforce RLS policies**. All 23 tenant-scoped models have explicit `organization_id` columns and proper indexing. RLS implementation is deferred to **Phase S2** but can begin in **Phase S1** as optional hardening.

---

## RLS Readiness Matrix

| Model | Has organization_id | Has Index | RLS Ready | Status |
|-------|-------------------|-----------|-----------|--------|
| **Client** | ✅ (direct FK) | ✅ (implicit via unique_together) | READY | ✅ |
| **Product** | ✅ (direct FK) | ✅ (implicit via unique_together) | READY | ✅ |
| **Category** | ✅ (direct FK) | ⚠️ Missing | PARTIAL | ⚠️ |
| **Supplier** | ✅ (direct FK) | ⚠️ Missing | PARTIAL | ⚠️ |
| **Warehouse** | ✅ (direct FK) | ⚠️ Missing | PARTIAL | ⚠️ |
| **Stock** | ✅ (direct FK) | ⚠️ Missing | PARTIAL | ⚠️ |
| **StockMovement** | ✅ (direct FK) | ✅ (inherited via Stock) | READY | ✅ |
| **PurchaseOrder** | ✅ (direct FK) | ⚠️ Missing | PARTIAL | ⚠️ |
| **PurchaseOrderItem** | ✅ (direct FK) | ⚠️ Missing | PARTIAL | ⚠️ |
| **Order** | ✅ (direct FK) | ✅ (via Django ORM PKs) | READY | ✅ |
| **OrderItem** | ✅ (direct FK) | ✅ (inherited via Order FK) | READY | ✅ |
| **OrderReturn** | ✅ (direct FK) | ✅ (inherited via Order FK) | READY | ✅ |
| **Payment** | ✅ (direct FK) | ✅ (inherited via Order FK) | READY | ✅ |
| **TaxConfiguration** | ✅ (direct FK) | ⚠️ Missing | PARTIAL | ⚠️ |
| **SalesReport** | ✅ (direct FK) | ⚠️ Missing | PARTIAL | ⚠️ |
| **CashReconciliation** | ✅ (direct FK) | ⚠️ Missing | PARTIAL | ⚠️ |
| **CompanyInvoiceConfig** | ✅ (direct FK) | ⚠️ Missing | PARTIAL | ⚠️ |
| **AccountingEntry** | ✅ (direct FK) | ✅ (organization, entry_date + entry_type) | READY | ✅ |
| **AccountingEntryLine** | ⚠️ (inherited via FK) | ⚠️ Missing | PARTIAL | ⚠️ |
| **InvoiceSyncQueue** | ✅ (direct FK) | ✅ (status, next_retry_at + organization, status) | READY | ✅ |
| **OrderWorkflowLog** | ✅ (direct FK) | ⚠️ Missing | PARTIAL | ⚠️ |
| **ExternalServiceConfig** | ✅ (direct FK) | ✅ (organization, provider_name) | READY | ✅ |
| **ExternalRequestLog** | ✅ (direct FK) | ✅ (organization + columns, order + provider_name) | READY | ✅ |

---

## RLS Policy Template

Once implemented (S2), each tenant-scoped table would have:

```sql
-- Enable RLS on tenant-scoped table
ALTER TABLE domain_order ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their organization's rows
CREATE POLICY organization_isolation ON domain_order
    USING (organization_id = current_setting('app.current_org_id')::UUID)
    WITH CHECK (organization_id = current_setting('app.current_org_id')::UUID);

-- Policy: Superusers with explicit X-Org-ID can access that org
CREATE POLICY superuser_org_access ON domain_order
    USING (
        (current_user_is_superuser AND organization_id = current_setting('app.current_org_id')::UUID)
        OR
        (NOT current_user_is_superuser AND organization_id IN (
            SELECT organization_id FROM domain_customuser WHERE id = current_setting('app.current_user_id')::UUID
        ))
    )
    WITH CHECK (organization_id = current_setting('app.current_org_id')::UUID);

-- Exempt superusers from RLS if needed (optional, for system operations)
-- ALTER ROLE "superuser_role" NOINHERIT;
```

---

## Indexing Recommendations for RLS

### Current Indexes (Good)
- ✅ `AccountingEntry`: `(organization_id, entry_date)` and `(organization_id, entry_type)`
- ✅ `InvoiceSyncQueue`: `(organization_id, status)` and `(status, next_retry_at)`
- ✅ `ExternalRequestLog`: `(organization_id, provider_name, created_at)` and `(order_id, provider_name)`
- ✅ `ExternalServiceConfig`: `(organization_id, provider_name)`

### Missing Indexes (Recommended for S1)

| Table | Recommended Index | Reason |
|-------|-------------------|--------|
| `domain_category` | `(organization_id)` | Frequently filtered by org; high cardinality |
| `domain_supplier` | `(organization_id)` | Used in PO queries; org-scoped |
| `domain_warehouse` | `(organization_id)` | Stock/inventory queries |
| `domain_stock` | `(organization_id, warehouse_id)` | Inventory dashboards |
| `domain_purchaseorder` | `(organization_id, status)` | PO status tracking |
| `domain_purchaseorderitem` | `(organization_id)` | Inherited via PurchaseOrder |
| `domain_taxconfiguration` | `(organization_id)` | Config lookups |
| `domain_salesreport` | `(organization_id, generated_at)` | Report queries by date |
| `domain_cashreconciliation` | `(organization_id, closed_at)` | Reconciliation queries |
| `domain_companyinvoiceconfig` | `(organization_id)` | Invoice config lookups |
| `domain_orderworkflowlog` | `(organization_id, timestamp)` | Workflow audit queries |
| `domain_accountingentryline` | `(organization_id)` via parent | Ledger queries |

---

## Implementation Roadmap (S1 vs S2)

### Phase S1 (Current)
- ✅ Document RLS requirements
- ✅ Add missing indexes to support RLS queries
- ⏸️ Do NOT enable RLS yet (would break application without app-side changes)

### Phase S2 (Future)
- 🔧 Update Django ORM context manager to set `app.current_org_id` GUC
- 🔧 Create RLS policies on all tables
- 🔧 Test RLS + TenantManager interaction
- 🔧 Deprecate `all_objects` manager (no longer needed with RLS)

---

## Pseudo-Code: RLS + Django Integration (S2)

```python
# In src/infrastructure/multitenancy/rls_context.py (new file)

from django.db import connection
from .thread_local import get_current_organization

class RLSContextManager:
    """
    Sets PostgreSQL session GUC variables for RLS.
    Called automatically on every request.
    """
    
    def __enter__(self):
        org_id = get_current_organization()
        if org_id:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET app.current_org_id = %s",
                    [str(org_id)]
                )
        return self
    
    def __exit__(self, *args):
        with connection.cursor() as cursor:
            cursor.execute("RESET app.current_org_id")

# Usage in middleware or ViewSet
def process_request(request):
    org_id = resolve_tenant_from_request(request)
    with RLSContextManager(org_id):
        # All queries inside this context use RLS
        orders = Order.objects.all()  # RLS filters by org_id automatically
```

---

## RLS vs TenantManager Trade-Offs

| Aspect | TenantManager (Current) | RLS (S2) |
|--------|----------------------|---------|
| **Enforcement** | Application layer | Database layer |
| **Bypassable** | Yes (via `.all_objects`) | No (cryptographic guarantee) |
| **Performance** | Slight overhead (Python filter) | Minimal overhead (PostgreSQL native) |
| **Debuggability** | Easy to trace in code | Harder to debug (SQL-side) |
| **Superuser Escalation** | Possible with careful header check | Impossible without explicit policy |
| **Compliance** | Auditable via code + logs | Auditable via audit logs + policies |

---

## Global Model: ExchangeRate (No RLS Needed)

`ExchangeRate` intentionally has no `organization_id` and should NOT have RLS. It's a reference table shared across all tenants. No changes required.

---

## Compliance & RLS

### SOC2 Readiness
- ✅ TenantManager provides *logical* isolation (testable, auditable)
- ✅ RLS would provide *cryptographic* isolation (stronger guarantee)
- ⏸️ Current state: PARTIAL (application-enforced, no database-level guarantee)
- 🎯 Post-S2: STRONG (database-enforced RLS)

### GDPR / Privacy
- Current: Data access controlled by application role logic + JWT claims
- With RLS: Data access guaranteed by PostgreSQL, even if app is compromised

---

## Risk: RLS Without Application Changes

**WARNING**: Enabling RLS without updating application code to set GUCs will **break all queries** because queries will be filtered to NULL (no org context).

**Must do in same PR**:
1. Add `RLSContextManager` middleware
2. Enable RLS policies
3. Test comprehensive query scenarios
4. Keep `all_objects` for admin operations (mark as deprecated)

---

## Recommendation

1. **S1 (Immediate)**: Add missing indexes to prepare for RLS
2. **S1 (Optional Hardening)**: Begin RLS implementation if resource-available
3. **S2 (Planned)**: Complete RLS rollout and deprecate `.all_objects`

---

## Next Step

See `docs/security/tenant_boundary_test_plan.md` Section "RLS Testing" for how to validate RLS policies in S2.
