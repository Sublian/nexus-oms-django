# S0.3: Superuser Governance Review

**Date**: 2026-06-19  
**Status**: Complete  
**Scope**: Authentication, Authorization, Role-based Access Control (RBAC), Superuser Privileges

---

## Executive Summary

Nexus OMS supports two privilege hierarchies that **can conflict**:

1. **Django Superuser** (`is_superuser=True`) — global bypass of all permissions
2. **Tenant Role** (`UserRole: ADMIN | STAFF | VIEWER`) — organizational role limited by tenant

**Current Design**: Superusers can bypass tenant isolation via X-Org-ID header but are NOT required to present explicit credentials per organization. This creates a high-risk escalation path (T6) requiring governance controls.

---

## Privilege Model

### Role Definitions

| Role | Scope | Permissions | Example Use |
|------|-------|-------------|-------------|
| **ADMIN** | Single Tenant | Full CRUD on all tenant data; manage users | Tenant owner, finance manager |
| **STAFF** | Single Tenant | Create/update orders, inventory; read-only reports | Sales operator, warehouse staff |
| **VIEWER** | Single Tenant | Read-only across all entities | Auditor, read-only stakeholder |
| **Superuser** | All Tenants | Global bypass; can assume any org via X-Org-ID | Platform support, admin |

### Superuser Implementation

```python
class CustomUser(AbstractUser):
    organization = ForeignKey(Organization, null=True, blank=True)  # ← nullable!
    role = CharField(choices=[ADMIN, STAFF, VIEWER], default=STAFF)
    is_superuser = BooleanField()  # Django's global permission flag
    is_staff = BooleanField()       # Django's staff flag
```

**Key Issue**: A superuser can exist with `organization=NULL`. This design permits:
- Superusers without tenant affiliation (centralized admins)
- Cross-tenant queries without explicit org-scoping
- No audit trail of which org a superuser accessed

---

## Current Governance (Actual)

### 1. Superuser Privilege Escalation

**Code**: `src/interfaces/api/views.py:39-44`
```python
class TenantViewMixin:
    def get_organization(self):
        user = self.request.user
        if user.is_superuser:
            org_id = self.request.META.get('HTTP_X_ORG_ID')
            return get_object_or_404(Organization, id=org_id) if org_id else None
        return user.organization
```

**Behavior**:
- ✅ Regular users: forced to use their assigned organization
- ❌ Superusers: can query ANY org via X-Org-ID header, or get None (→ leaks all data)
- ❌ No audit log of which org superuser accessed
- ❌ No rate limiting on cross-org queries

---

### 2. Role Enforcement

**Where**: Django admin interface and custom permission checks (minimal)

**Issue**: Only basic Django permission framework. No custom RBAC enforcement in API ViewSets.

**Example Missing Check**:
```python
# Currently missing in OrderViewSet
if user.role == VIEWER:
    # Should reject write operations (POST, PATCH, DELETE)
    # But code currently allows them!
```

---

### 3. Superuser as Maintenance Escalation

**Intended Use**: Platform engineers using superuser account for:
- Database migrations
- Manual data corrections
- Bulk operations across all tenants
- Emergency incident response

**Risk**: Without governance, this becomes the default path for operations instead of least-privilege alternatives.

---

## Governance Gap Analysis

### Gap G1: No Explicit Superuser Authorization Model

**Issue**: Superuser can query any org without explicit per-org credentials or approval workflows.

**Current State**: `if user.is_superuser` is the only guard.

**Risk**: Privilege escalation; insider threat (disgruntled admin accessing competitor's data).

**Example Attack**:
```bash
curl -H "Authorization: Bearer <superuser_token>"
     -H "X-Org-ID: competitor-org-uuid"
     https://nexus.com/api/v1/orders/
# Returns ALL orders from competitor org
```

---

### Gap G2: No Audit Trail for Superuser Actions

**Issue**: No logging of:
- Which superuser accessed which org
- What data was queried
- When the escalation happened

**Current State**: Requests are logged in `ExternalRequestLog`, but superuser identity is not captured separately.

**Risk**: Compliance violation (GDPR, SOC2); no forensic trail for incident investigation.

---

### Gap G3: No Rate Limiting on Superuser Queries

**Issue**: Superuser can bulk-export all tenant data without triggering alerts.

**Current State**: Same rate limits apply to superusers as regular users (if any).

**Risk**: Data exfiltration; denial of service via bulk queries.

---

### Gap G4: No Explicit Opt-In for Superuser Without Organization

**Issue**: `CustomUser.organization` can be NULL, but there's no workflow to ensure:
- Superusers are created intentionally
- Role field reflects their actual responsibilities
- Superusers are tied to a formal security review

**Current State**: Superusers can be created via Django admin with no additional checks.

**Risk**: Accidental creation of orph an superuser accounts; misuse of legacy accounts.

---

### Gap G5: Role Enforcement Missing in API Tier

**Issue**: VIEWER users should not create/update/delete, but ViewSet `.create()` methods don't check role.

**Current State**: Only `organization` is checked; role is not enforced.

**Risk**: Authorization bypass; VIEWER users can modify data.

---

## Tenant Boundary Violations by Superuser

### Scenario: Superuser Escalation to Competitor Data

1. Superuser (`is_superuser=True`, `organization=NULL`)
2. Calls `GET /api/v1/orders/` with `X-Org-ID: competitor-uuid`
3. `TenantViewMixin.get_organization()` returns competitor's org
4. `OrderViewSet.get_queryset()` filters by that org
5. **BUT** if X-Org-ID is missing, query returns `Order.all_objects.all()` (all tenants)

**Impact**: CRITICAL data breach

---

### Scenario: Superuser as Maintenance, Leaves Company

1. Departed engineer still has superuser token (token not revoked immediately)
2. Can query any org without needing that org's credentials
3. No audit log connects the token to which org was accessed
4. Compliance investigation is blind

**Impact**: Data exfiltration; regulatory exposure

---

## Mitigation Strategy (T6 — Superuser Governance)

### T6.1: Require Explicit Org for Superuser Queries

**Implementation**:
```python
class TenantViewMixin:
    def get_organization(self):
        user = self.request.user
        if user.is_superuser:
            org_id = self.request.META.get('HTTP_X_ORG_ID')
            if not org_id:
                raise PermissionDenied("Superuser must provide X-Org-ID header")
            return get_object_or_404(Organization, id=org_id)
        return user.organization
```

**Effect**: Closes the `all_objects.all()` leak by forcing superuser to name the org.

---

### T6.2: Audit Superuser Access

**Implementation**:
```python
# In middleware or ViewSet.dispatch()
if request.user.is_superuser:
    log_superuser_access(
        user_id=request.user.id,
        organization_id=org_id,
        endpoint=request.path,
        timestamp=now(),
    )
```

**Effect**: Forensic trail for incident investigation.

---

### T6.3: Enforce Role-Based RBAC in ViewSets

**Implementation**:
```python
class OrderViewSet(viewsets.ModelViewSet):
    def create(self, request, *args, **kwargs):
        if request.user.role == UserRole.VIEWER:
            raise PermissionDenied("VIEWER role cannot create orders")
        # ... proceed
```

**Effect**: Role becomes a real enforcing guard, not just UI guidance.

---

### T6.4: Limit Superuser Token Lifetime

**Implementation**: Shorten superuser token expiry (e.g., 15 min instead of 1 hour) to reduce window of compromise.

---

### T6.5: Require Multi-Factor Authentication for Superuser

**Implementation**: Superuser tokens only issued after TOTP/MFA challenge.

---

## RLS as Ultimate Superuser Mitigation (Future: S2)

Even with governance controls, database-level Row-Level Security (RLS) would ensure:
- Superuser cannot query data outside their org, even with `.all_objects`
- Governance violations are caught by the database, not application logic

Example:
```sql
CREATE POLICY organization_isolation ON "Order"
    USING (organization_id = current_setting('app.current_org_id')::UUID);
```

**Status**: Blocked for S0; targets S2 RLS hardening phase.

---

## Superuser Governance Controls Register

| Control ID | Description | Phase | Priority |
|-----------|-------------|-------|----------|
| **T6.1** | Require X-Org-ID header for superuser queries | S1 | CRITICAL |
| **T6.2** | Log all superuser org access attempts | S1 | HIGH |
| **T6.3** | Enforce role-based RBAC in ViewSets | S1 | HIGH |
| **T6.4** | Shorten superuser token lifetime | S1 | MEDIUM |
| **T6.5** | Require MFA for superuser token issuance | S2 | MEDIUM |
| **T6.6** | Implement RLS as enforcement layer | S2 | HIGH |
| **T6.7** | Quarterly superuser account audit | Operations | MEDIUM |

---

## Recommendation

**S1 Priority**: Implement T6.1 + T6.2 to close the unguarded superuser escalation path and establish audit trail. Defer T6.4 + T6.5 to S2 hardening.

**Next Step**: See `docs/security/tenant_boundary_test_plan.md` section "Superuser Isolation Tests" for how to validate superuser governance in S1.
