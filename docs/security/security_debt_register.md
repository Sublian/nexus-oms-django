# S0.6: Security Debt Register

**Date**: 2026-06-19  
**Status**: Open (Discovery Phase)  
**Scope**: Known security risks accepted for future remediation

---

## Register Overview

All security debts are tracked with:
- **ID**: Unique identifier (SD-NNN)
- **Description**: What is the risk?
- **Risk Level**: CRITICAL | HIGH | MEDIUM | LOW
- **Accepted Date**: When was this risk formally accepted?
- **Target Remediation Phase**: S1 | S2 | S3 | Deferred
- **Acceptance Rationale**: Why are we accepting this now?
- **Responsible**: Owner for remediation

---

## Active Security Debt

### SD-001: Taxonomía Transitoria en Texto Libre (ExternalRequestLog.error_message)

| Field | Value |
|-------|-------|
| **ID** | SD-001 |
| **Severity** | MEDIUM |
| **Status** | OPEN |
| **Category** | Data Quality / Observability Debt |

**Description**:

`ExternalRequestLog.error_message` stores free-form error text from external providers (Nubefact, SUNAT, etc.) without standardized taxonomy. Examples:

```
"Nubefact API returned 400: Invalid invoice total"
"Connection timeout after 15 seconds"
"SUNAT returned REJECTED: Document already registered"
"Internal Server Error"
```

This creates:
1. **Unmeasurable observability**: Can't aggregate errors into metrics
2. **Inconsistent remediation**: Support team must parse strings manually
3. **Log injection risk**: Unvalidated provider errors could contain sensitive data or exploit patterns

**Risk Level**: MEDIUM (observability, not data breach)

**Why Accepted Now**:
- Nubefact/SUNAT integrations are young; error taxonomy not yet stable
- Support team currently handles errors via manual parsing (acceptable for low volume)
- Capturing full text is better than losing error context

**Target Remediation**: S1 (during invoice refactor)

**Acceptance Date**: 2026-06-19

**Acceptance Rationale**:
> "Phase 4a established the invoice sync queue structure with functional retry logic. Standardizing error taxonomy requires API provider stability and clearer error categorization. This is deferred to S1 invoice hardening when provider integrations mature. Log injection is mitigated by INPUT VALIDATION at handler level (see src/infrastructure/services/)."

**Responsible**: Luis Gonzalez (Architecture)

**Remediation Plan**:

```python
# S1 Migration: Create ErrorTaxonomy model
class ExternalProviderError(models.TextChoices):
    TIMEOUT = 'timeout', 'Request timeout'
    INVALID_CREDENTIALS = 'invalid_creds', 'Invalid API credentials'
    INVALID_DATA = 'invalid_data', 'Invalid document data'
    ALREADY_EXISTS = 'already_exists', 'Document already processed'
    RATE_LIMITED = 'rate_limited', 'Rate limit exceeded'
    PROVIDER_ERROR = 'provider_error', 'Provider internal error'
    UNKNOWN = 'unknown', 'Unknown error'

# Update ExternalRequestLog
class ExternalRequestLog(TenantModel):
    error_type = CharField(choices=ErrorTaxonomy.choices, null=True)  # NEW
    error_message = TextField(null=True)  # Existing; still captured
    
    def categorize_error(self):
        # Auto-categorize based on provider response code + message pattern
        if 'timeout' in self.error_message.lower():
            self.error_type = ErrorTaxonomy.TIMEOUT
        # ...
```

**Success Criteria (S1)**:
- [ ] All new ExternalRequestLog entries have error_type populated
- [ ] Backfill script categorizes existing errors
- [ ] Error dashboard aggregates by error_type
- [ ] Support team can filter by category

---

### SD-002: Superuser Escalation Without Explicit Org Requirement

| Field | Value |
|-------|-------|
| **ID** | SD-002 |
| **Severity** | CRITICAL |
| **Status** | OPEN |
| **Category** | Authorization |

**Description**:

API ViewSets allow superuser to query all tenant data by omitting X-Org-ID header, returning `all_objects.all()`. See full analysis in `docs/security/tenant_leak_audit.md` (Findings 1-4).

**Risk Level**: CRITICAL (data exfiltration, compliance violation)

**Why Accepted Now**:
- No production incidents yet (superuser base limited, trusted)
- Fix requires API ViewSet refactor
- Current risk is mitigated by superuser scarcity (only platform engineers)

**Target Remediation**: S1 (immediate priority)

**Acceptance Date**: 2026-06-19

**Acceptance Rationale**:
> "This is a **known architectural issue with time-bound acceptance**: S1 must close this vulnerability. Until then, deployment constraints are: (1) Restrict superuser token issuance to security-cleared platform engineers only, (2) Implement audit logging on all superuser API calls, (3) Require X-Org-ID header on all API requests."

**Responsible**: Luis Gonzalez (Architecture)

**Remediation Plan (S1 — CRITICAL)**:

1. Update `TenantViewMixin.get_organization()` to reject superuser without X-Org-ID:
   ```python
   def get_organization(self):
       user = self.request.user
       if user.is_superuser:
           org_id = self.request.META.get('HTTP_X_ORG_ID')
           if not org_id:
               raise PermissionDenied("Superuser must provide X-Org-ID header")
           return get_object_or_404(Organization, id=org_id)
       return user.organization
   ```

2. Update all API ViewSets to use:
   ```python
   def get_queryset(self):
       org = self.get_organization()  # Now never None for superuser
       return Model.objects.filter(organization=org)
   ```

3. Add audit logging for superuser access

**Success Criteria (S1)**:
- [ ] All API ViewSets reject superuser without X-Org-ID
- [ ] Test coverage: superuser + no X-Org-ID → 403 Forbidden
- [ ] Audit log captures all superuser org access
- [ ] Production deployment blocks unguarded superuser queries

---

### SD-003: Nullable Organization on CustomUser

| Field | Value |
|-------|-------|
| **ID** | SD-003 |
| **Severity** | HIGH |
| **Status** | OPEN |
| **Category** | Data Model |

**Description**:

`CustomUser.organization` is nullable (null=True, blank=True), allowing superusers to exist without organization affiliation. This design supports:
- Centralized platform admins
- Service accounts without tenant binding

However, it:
- Permits accidental creation of dangling superusers
- Lacks governance workflow

**Risk Level**: HIGH (potential for unauthorized escalation, no audit trail of intent)

**Why Accepted Now**:
- Intentional design for superuser pattern
- Governance controls (T6) deferred to S1
- Risk mitigated by RBAC in S1

**Target Remediation**: S1 (governance) + S2 (RLS)

**Acceptance Date**: 2026-06-19

**Acceptance Rationale**:
> "This is an **intentional design decision** to support platform administrators. Mitigation in S1: Implement T6.1 + T6.2 (require X-Org-ID for superusers, audit logging). Future S2: Add RLS policy enforcement."

**Responsible**: Luis Gonzalez (Architecture)

**Remediation Plan**:

- **S1**: Implement T6 (Superuser Governance) — see `docs/security/superuser_governance.md`
- **S2**: Implement RLS; enforce database-level org_id checks

**Success Criteria (S1)**:
- [ ] T6.1: Superuser API calls require X-Org-ID header
- [ ] T6.2: All superuser access logged with timestamp + org_id
- [ ] Quarterly superuser account audit process documented

---

### SD-004: No Encryption at Rest for Sensitive Fields

| Field | Value |
|-------|-------|
| **ID** | SD-004 |
| **Severity** | HIGH |
| **Status** | OPEN |
| **Category** | Data Protection |

**Description**:

Sensitive fields (api_key, api_secret, payment info) are stored in plaintext in PostgreSQL:

- `ExternalServiceConfig.api_key` — Nubefact API credentials
- `ExternalServiceConfig.api_secret` — Secondary secret
- `Payment.transaction_reference` — Payment gateway references (not full PAN, but sensitive)

If database is breached or exported, credentials are immediately usable by attacker.

**Risk Level**: HIGH (credential compromise; GDPR/PCI-DSS concern)

**Why Accepted Now**:
- Development database unencrypted (acceptable for non-prod)
- Production uses PostgreSQL SSL + network isolation (partial mitigation)
- Full field-level encryption requires key management infrastructure

**Target Remediation**: S2 (deferred to hardening phase)

**Acceptance Date**: 2026-06-19

**Acceptance Rationale**:
> "Phase S0-S1 focus on application-layer isolation (RLS, masking). At-rest encryption is a S2 hardening task. Interim mitigation: Database access restricted to app container + admin users; no direct DB exports; secrets never logged in plaintext."

**Responsible**: Luis Gonzalez (Infrastructure)

**Remediation Plan (S2)**:

1. Implement Django field-level encryption using `django-encrypted-model-fields`
2. Integrate with AWS KMS or HashiCorp Vault for key management
3. Rotate keys quarterly

**Success Criteria (S2)**:
- [ ] ExternalServiceConfig.api_key encrypted at rest
- [ ] ExternalServiceConfig.api_secret encrypted at rest
- [ ] Key rotation process automated
- [ ] Test: unauthorized DB access cannot read secrets

---

### SD-005: No Role-Based RBAC Enforcement in API ViewSets

| Field | Value |
|-------|-------|
| **ID** | SD-005 |
| **Severity** | MEDIUM |
| **Status** | OPEN |
| **Category** | Authorization |

**Description**:

`CustomUser.role` (ADMIN | STAFF | VIEWER) is defined but not enforced. ViewSets allow VIEWER users to create/update/delete data:

```python
class OrderViewSet(viewsets.ModelViewSet):
    def create(self, request):
        # No check: if user.role == VIEWER, reject POST
        # VIEWER user can currently create orders!
```

**Risk Level**: MEDIUM (authorization bypass; less critical than SD-002)

**Why Accepted Now**:
- Current user base small and trusted
- Django admin permissions provide partial coverage
- RBAC enforcement easy to add in S1

**Target Remediation**: S1

**Acceptance Date**: 2026-06-19

**Acceptance Rationale**:
> "Role field was added for future RBAC but not yet wired into ViewSets. S1 will enforce role-based method permissions in all write operations."

**Responsible**: Luis Gonzalez (API)

**Remediation Plan (S1)**:

```python
# Create permission mixins
class AdminOnlyMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.role != UserRole.ADMIN and not request.user.is_superuser:
            raise PermissionDenied("Admin role required")
        return super().dispatch(request, *args, **kwargs)

class StaffOrAdminMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in [UserRole.ADMIN, UserRole.STAFF] and not request.user.is_superuser:
            raise PermissionDenied("Staff or Admin role required")
        return super().dispatch(request, *args, **kwargs)

# Apply to ViewSets
class OrderViewSet(StaffOrAdminMixin, viewsets.ModelViewSet):
    # Create/Update/Delete now require STAFF or ADMIN
    pass
```

**Success Criteria (S1)**:
- [ ] VIEWER users get 403 on POST/PATCH/DELETE
- [ ] STAFF users can create but not delete
- [ ] ADMIN users have full CRUD
- [ ] Test coverage for all role+method combinations

---

### SD-006: No MFA for Superuser Token Issuance

| Field | Value |
|-------|-------|
| **ID** | SD-006 |
| **Severity** | MEDIUM |
| **Status** | OPEN |
| **Category** | Authentication |

**Description**:

Superuser can obtain JWT token with just email + password. No multi-factor authentication (MFA) required, increasing token theft risk.

**Risk Level**: MEDIUM (applies only to superuser; regular users acceptable)

**Why Accepted Now**:
- Superuser base small (platform engineers only)
- MFA integration requires auth provider setup
- S1 priority: close SD-002 (escalation); defer MFA to S2

**Target Remediation**: S2

**Acceptance Date**: 2026-06-19

**Acceptance Rationale**:
> "Superuser MFA is a hardening task for S2. Interim mitigation: Strict control of superuser account creation; token monitoring; short expiry (1 hour)."

**Responsible**: Luis Gonzalez (Infrastructure)

---

## Summary Table

| ID | Description | Severity | Phase | Status | Responsible |
|----|-------------|----------|-------|--------|-------------|
| **SD-001** | Error taxonomy in text free-form | MEDIUM | S1 | OPEN | Luis Gonzalez |
| **SD-002** | Superuser escalation without X-Org-ID | CRITICAL | S1 | OPEN | Luis Gonzalez |
| **SD-003** | Nullable organization on CustomUser | HIGH | S1+S2 | OPEN | Luis Gonzalez |
| **SD-004** | No encryption at rest (credentials) | HIGH | S2 | OPEN | Luis Gonzalez |
| **SD-005** | No RBAC enforcement in ViewSets | MEDIUM | S1 | OPEN | Luis Gonzalez |
| **SD-006** | No MFA for superuser | MEDIUM | S2 | OPEN | Luis Gonzalez |

---

## Phase 4B Freeze

**Announcement**: Phase 4B (Dashboard) is officially **frozen in backlog** until S1 security hardening is complete. All new feature development pauses. Focus: S0 discovery → S1 security implementation.

**Why**: SD-002, SD-003, SD-005 block production readiness. Dashboard features depend on secure RBAC/tenant isolation.

**Target Unfreeze**: 2026-07-15 (post-S1 review)

---

## Governance Notes

All debts require:
1. ✅ Formal acceptance (this register)
2. ✅ Risk quantification
3. ✅ Remediation timeline
4. ✅ Owner assignment
5. ✅ Audit tracking

Debts are **never silently closed**; closure requires evidence of remediation.

---

## References

- [OWASP Technical Debt Tracking](https://owasp.org/www-community/Technical_Debt)
- Nexus OMS: `docs/security/tenant_leak_audit.md` (S0.2)
- Nexus OMS: `docs/security/superuser_governance.md` (S0.3)
