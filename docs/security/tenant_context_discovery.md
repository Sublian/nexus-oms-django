# S1.0: Tenant Context Discovery & Infrastructure Flow Audit

**Date**: 2026-06-19  
**Status**: Complete (Inspection Only)  
**Scope**: Physical tracing of `organization_id` from origin to every execution path

---

## Executive Summary

Tenant context (`organization_id`) originates from **3 fragmented sources** that are never consolidated:
1. **JWT Claims** (embedded but NEVER extracted/used by middleware)
2. **User.organization FK** (assigned but not automatically propagated)
3. **X-Org-ID Header + URL Slug** (extracted by middleware, propagated via thread-local)

This fragmentation creates coupling and leakage risk. There is **NO single source of truth**.

---

## Pregunta 1: ¿Dónde Nace `organization_id`?

### Origin Point 1A: JWT Token Issuance

**File**: `src/interfaces/api/serializers.py:57-66`

```python
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extiende el token JWT con claims del tenant y rol del usuario."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['role'] = user.role
        token['organization_id'] = str(user.organization_id) if user.organization_id else None  # ← JWT CLAIM
        return token
```

**Evidence**:
- JWT token includes `organization_id` claim
- BUT this claim is NEVER extracted by middleware (see Pregunta 2)
- The claim is **embedded but unused** — dead code

---

### Origin Point 1B: User Model Organization FK

**File**: `src/domain/models/users.py:35-50`

```python
class CustomUser(AbstractUser):
    organization = ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name='users',
        null=True,   # ← nullable: allows superusers without org
        blank=True,
    )
    role = CharField(
        max_length=10,
        choices=UserRole.choices,
        default=UserRole.STAFF,
    )
```

**Evidence**:
- `CustomUser.organization` is the authoritative org assignment for a user
- Nullable: allows org-less superusers
- Used in middleware as fallback (`return user.organization` if no X-Org-ID)

---

### Origin Point 1C: X-Org-ID Header (Superuser Escalation)

**File**: `src/interfaces/api/views.py:39-44`

```python
class TenantViewMixin:
    """Resuelve la organización activa desde el usuario autenticado.
    Superusuarios pueden apuntar a cualquier org via X-Org-ID header.
    """
    def get_organization(self):
        user = self.request.user
        if user.is_superuser:
            org_id = self.request.META.get('HTTP_X_ORG_ID')  # ← EXPLICIT HEADER
            return get_object_or_404(Organization, id=org_id) if org_id else None
        return user.organization
```

**Evidence**:
- Superusers can specify ANY org via X-Org-ID header
- X-Org-ID is OPTIONAL and MANUAL
- No automated extraction from JWT claim
- Enables superuser escalation (SD-002)

---

## Pregunta 2: ¿Cómo Viaja hasta la Vista?

### Journey: Request → Middleware → Thread-Local → QuerySet

**File**: `src/infrastructure/multitenancy/middleware.py:8-50`

```python
class OrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        org = None
        
        # Step 1: Try X-Org-ID header (API calls)
        org_id = request.headers.get('HTTP_X_ORG_ID')
        if org_id:
            try:
                org = Organization.objects.get(id=org_id)
            except (Organization.DoesNotExist, ValueError):
                pass
        
        # Step 2: Try URL slug (Web/Dashboard)
        if not org:
            match = re.search(r'^/dashboard/([^/]+)/', request.path)
            if match:
                slug = match.group(1)
                try:
                    org = Organization.objects.get(slug=slug)
                except Organization.DoesNotExist:
                    pass
        
        # Step 3: Set request context + thread-local
        try:
            if org:
                request.organization = org  # ← For context processor
                set_current_organization(org.id)  # ← For TenantManager
            else:
                request.organization = None
            
            response = self.get_response(request)
            return response
        finally:
            clear_current_organization()  # ← CRITICAL: cleanup
```

**Evidence**:
- **NOT using JWT claim** (`organization_id` token claim is ignored)
- Two extraction paths:
  1. X-Org-ID header (API) — **MANUAL, MUST BE PROVIDED**
  2. URL slug (Web) — **automatic, slug from path**
- Sets `request.organization` for context processors
- Sets thread-local `organization_id` for TenantManager

**Critical Gap**:
```
JWT Claim org_id ──→ (UNUSED) ✗
User.organization ──→ (only used if no X-Org-ID)
X-Org-ID Header ──→ (manual, optional for superuser)
URL Slug ──→ (web views only)
```

### Flow Diagram

```
HTTP Request
  ↓
Middleware.OrganizationMiddleware
  ├─ Extract X-Org-ID header? (API)
  ├─ Extract URL slug? (Web)
  └─ Set request.organization + thread-local org_id
       ↓
    TenantManager.get_queryset()
      └─ Filter by thread-local org_id (if set)
           ↓
        .objects queries (app views, services)
```

---

## Pregunta 3: ¿Cómo Llega a Celery?

### Path: Task Parameter → .all_objects → explicit organization filter → UseCase

**File**: `src/domain/tasks/sync_invoice_tasks.py:49-162`

**Phase 1: Task Dispatch**
```python
@shared_task(bind=True, name="tasks.sync_pending_invoices")
def sync_pending_invoices_task(self):
    """Barre todas las entradas pendientes y despacha una task por cada una."""
    now = timezone.now()
    entry_ids = list(
        InvoiceSyncQueue.all_objects  # ← USES .all_objects to bypass tenant filtering
        .filter(status=InvoiceSyncQueue.STATUS_PENDING, next_retry_at__lte=now)
        .values_list('id', flat=True)
    )
    
    for entry_id in entry_ids:
        sync_single_invoice_task.delay(entry_id)  # ← PASSES entry_id, not org_id
```

**Phase 2: Per-Entry Task**
```python
@shared_task(bind=True, name="tasks.sync_single_invoice", max_retries=0)
def sync_single_invoice_task(self, entry_id: int):
    # Phase 1: Lock + idempotence
    with transaction.atomic():
        entry = (
            InvoiceSyncQueue.all_objects  # ← Uses .all_objects (no thread-local context)
            .select_for_update()
            .select_related('order')
            .get(id=entry_id)
        )
    
    # Capture org_id from fetched object
    org_id = entry.organization_id  # ← EXTRACTED FROM DATABASE OBJECT
    
    # Phase 2: Call UseCase (NO set_current_organization() call!)
    result = InvoiceStatusQueryUseCase().execute(entry)
```

**File**: `src/application/usecases/query_invoice_status.py:26-42`

```python
def execute(self, sync_entry) -> dict:
    order = sync_entry.order
    
    if self._provider is not None:
        provider = self._provider
    else:
        try:
            # ← Uses .objects (TenantManager) with explicit organization filter
            config = CompanyInvoiceConfig.objects.get(organization=order.organization)
        except CompanyInvoiceConfig.DoesNotExist:
            raise NubefactPermanentError(...)
        provider = get_invoice_provider(config)
    
    result = provider.get_invoice_status(order, order.invoice_external_id)
    # ...
    return result
```

### Evidence

| Step | Code | Mechanism | Fragility |
|------|------|-----------|-----------|
| **Dispatch** | `sync_pending_invoices_task()` | Uses `.all_objects` to query all tenants | ✓ Correct |
| **Entry Fetch** | `entry_id` parameter only | Fetches entry via `.all_objects` | ✓ Correct |
| **Org Extraction** | `org_id = entry.organization_id` | Reads from fetched object | ✓ Explicit |
| **UseCase Call** | `InvoiceStatusQueryUseCase().execute(entry)` | NO thread-local context set | ⚠️ **FRAGILE** |
| **Query in UseCase** | `.objects.get(organization=...)` | Explicit filter + TenantManager (context=None) | ⚠️ **WORKS BY ACCIDENT** |

### Fragility Analysis

The UseCase works **by accident** because:
1. Thread-local context is `None` in Celery
2. TenantManager.get_queryset() returns all rows (no filtering)
3. Explicit `.filter(organization=...)` in UseCase then narrows down

**Risk**: If code changes and someone uses `.objects.filter()` without explicit `organization=`, it would return all rows!

**Missing**: Should call `set_current_organization(org_id)` before UseCase.

---

## Pregunta 4: ¿Cómo Llega a los Comandos Administrativos?

### Management Command: Explicit Context Management

**File**: `src/domain/management/commands/seed_data.py:27-88`

```python
def handle(self, *args, **options):
    # ...
    for config in org_configs:
        try:
            with transaction.atomic():
                org, _ = Organization.objects.update_or_create(
                    slug=config['slug'],
                    defaults={...},
                )
                
                set_current_organization(org.id)  # ← EXPLICIT SET
                
                # Now all .objects queries respect context
                tax_rate_dec = Decimal(str(config['tax']))
                TaxConfiguration.objects.update_or_create(
                    organization=org, is_default=True,  # ← Explicit + context
                    defaults={...},
                )
                
                warehouse, _ = Warehouse.objects.get_or_create(
                    name='Bodega Central', organization=org
                )
                
                # ... more operations ...
                
        finally:
            clear_current_organization()  # ← ALWAYS CLEANUP
```

### Evidence

- ✅ Commands **explicitly manage** thread-local context
- ✅ Each org gets its own context block
- ✅ Cleanup in finally block (even on exception)
- ✅ Commands are tenant-aware and safe

---

## Pregunta 5: ¿Cómo Llega a los Tests?

### Test Fixtures: Manual Organization Assignment (No Context Setting)

**File**: `src/tests/conftest.py:40-68`

```python
@pytest.fixture
def org_factory(db):
    """Factory para crear múltiples organizaciones sin choque de slugs."""
    def _make_org(name):
        return Organization.objects.create(
            name=name, 
            slug=name.lower().replace(" ", "-")
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
        organization=organization  # ← EXPLICIT organization= parameter
    )
```

**File**: `src/tests/domain/services/test_order_service.py:14-50`

```python
@pytest.mark.django_db
class TestOrderReturn:
    
    def test_return_fails_if_quantity_is_zero(self, organization, product):
        order = Order.objects.create(
            organization=organization,  # ← EXPLICIT: passing org to create
            customer_name="Luis"
        )
        
        with pytest.raises(ValidationError) as excinfo:
            OrderService.process_return(
                organization=organization,  # ← EXPLICIT: passing org to service
                order_id=order.id,
                product_id=product.id,
                quantity=0,
                reason="OTHERS"
            )
```

### Evidence

| Aspect | Status | Evidence |
|--------|--------|----------|
| **Fixture creates organization** | ✅ | `org_factory()` |
| **Fixture creates products per org** | ✅ | `organization=organization` param |
| **Tests set thread-local context** | ❌ | NO `set_current_organization()` in tests |
| **Tests pass explicit organization=** | ✅ | All `Order.objects.create(organization=...)` |
| **Tests validate TenantManager** | ❌ | Tests don't test automatic filtering |

### Test Gap

Tests manually assign `organization=` to every creation. This:
- ✅ Works for explicit queries
- ❌ **Doesn't validate TenantManager auto-filtering**
- ❌ **Doesn't catch if someone uses .all() instead of .objects**
- ❌ **Doesn't test tenant isolation at all**

**Missing**: Tests should:
1. Set thread-local context to Org A
2. Create order in Org A
3. Create order in Org B
4. Query via `.objects.all()` — should only see Org A
5. Verify Org B order is hidden

---

## Pregunta 6: ¿Existe una Fuente Única de Verdad?

### Single Source of Truth Assessment

**Candidate 1: JWT Claim `organization_id`**
- Embedded in token ✓
- NEVER extracted by middleware ✗
- Verdict: **NOT used, dead code**

**Candidate 2: User.organization FK**
- Assigned during user creation ✓
- Used as fallback in API (if no X-Org-ID) ✓
- Used in web views via middleware ✓
- Verdict: **Partial — only fallback, not for superusers**

**Candidate 3: X-Org-ID Header**
- Mandatory for superuser escalation ✓
- Optional for regular users ✗
- Manually specified by client ✗
- Verdict: **Fragmented — not automatic**

**Candidate 4: URL Slug (Web)**
- Automatic extraction ✓
- Web views only ✗
- Verdict: **Limited — web only**

### Verdict: NO Single Source of Truth

| Source | JWT | User.org | X-Org-ID | URL Slug | Commands |
|--------|-----|---------|----------|----------|----------|
| **API** | Embedded ✗ | Fallback ✓ | Primary ⚠️ | N/A | N/A |
| **Web** | Unused ✗ | Fallback | N/A | Primary ✓ | N/A |
| **Celery** | Unused ✗ | Unused ✗ | N/A | N/A | Explicit ✓ |
| **Tests** | Unused ✗ | Explicit ✓ | N/A | N/A | Explicit ✓ |

**Fragmentation Risk**:
```
If JWT claim differs from User.organization
  → API uses User.organization (ignores JWT)
  → Inconsistency, confusion

If X-Org-ID header differs from User.organization
  → Superuser can access wrong org
  → Deliberate (by design) OR mistake?

If URL slug differs from JWT claim
  → Web view uses slug, API would use User.org
  → Cross-layer inconsistency
```

---

## Exit Criteria Matrix: S1A Discovery

| Criterio | ✅/❌ | Justificación |
|----------|------|---------------|
| **¿Existe una fuente única de tenant?** | ❌ | 4 sources: JWT (unused), User.org (partial), X-Org-ID (manual), URL slug (web-only). No consolidation. |
| **¿Celery conserva el tenant?** | ⚠️ FRAGILE | Uses `.all_objects` (correct) but doesn't set thread-local context. Works by accident via explicit filters in UseCase. |
| **¿Los comandos administrativos son tenant-aware?** | ✅ | Explicit `set_current_organization()` + `clear_current_organization()` in finally. Fully tenant-aware. |
| **¿Los tests actuales simulan tenants correctamente?** | ❌ | Tests pass explicit `organization=` parameters but DON'T set thread-local context. Don't validate TenantManager auto-filtering. Gap: missing tenant isolation test suite. |

---

## Architectural Recommendations (S1 Implementation)

### R1: Consolidate to Single Source of Truth

**Action**: Extract `organization_id` from JWT claim in middleware

```python
# Proposed: Extract from JWT instead of header
def get_tenant_from_request(request):
    # Priority order:
    # 1. X-Org-ID header (superuser override)
    # 2. JWT claim (from token, most authoritative)
    # 3. User.organization FK (fallback)
    # 4. URL slug (web-specific)
```

### R2: Make Celery Context Explicit

**Action**: Wrap Celery tasks with context manager

```python
@shared_task
def sync_single_invoice_task(self, entry_id):
    entry = InvoiceSyncQueue.all_objects.get(id=entry_id)
    
    with TenantContextManager(org_id=entry.organization_id):
        result = InvoiceStatusQueryUseCase().execute(entry)
```

### R3: Test Tenant Isolation

**Action**: Implement S0.7 test plan (17 tests, 85% coverage)

---

## Files Inspected

- `src/interfaces/api/serializers.py` — JWT claim generation
- `src/interfaces/api/views.py` — TenantViewMixin, superuser escalation
- `src/domain/models/users.py` — CustomUser.organization FK
- `src/infrastructure/multitenancy/middleware.py` — Context extraction
- `src/infrastructure/multitenancy/thread_local.py` — Thread-local store
- `src/domain/tasks/sync_invoice_tasks.py` — Celery task implementation
- `src/application/usecases/query_invoice_status.py` — UseCase isolation
- `src/domain/management/commands/seed_data.py` — Command context management
- `src/tests/conftest.py` — Test fixtures
- `src/tests/domain/services/test_order_service.py` — Integration test example

---

## Conclusion: Fragmented, Fragile, but Functional

Current state: **Works in practice, fragmented in architecture**

- ✅ Middleware + thread-local provide automatic filtering for web/API requests
- ✅ Commands explicitly manage context
- ❌ JWT claim is dead code (never extracted)
- ❌ Multiple org sources create coupling and confusion
- ❌ Celery works by accident (explicit filters hide missing context)
- ❌ Tests don't validate automatic tenant isolation

**S1 Target**: Consolidate to single source, make context explicit everywhere, implement comprehensive test coverage.
