# Discovery Report: FASE 3.4A — Invoice Observability Audit
**Date:** June 14, 2026  
**Scope:** Payload persistence, error taxonomy, correlation traceability  
**Constraint:** Read-only audit (no schema or code changes)

---

## Executive Summary

Nexus OMS has **partial observability** of the invoice lifecycle. Payloads are persisted but fragmented across multiple models; error taxonomy is implicit rather than explicit; correlation traces Order.id consistently but external request logs are generated but unused.

| Finding | Status | Severity |
|---------|--------|----------|
| Payload persistence | ✅ Partial | Medium |
| Error sources structured | ❌ Not yet | Medium |
| Correlation candidate | ✅ Valid | Low |
| External request logging | ⚠️ Orphaned | Medium |

---

## 1. PAYLOAD DISCOVERY: Request/Response Persistence

### 1.1 Models with Payload Fields

#### `ExternalRequestLog` (src/domain/models/integrations.py)
**Status:** Model defined but **NOT ACTIVELY USED** in invoice flow.

```python
class ExternalRequestLog(TenantModel):
    request_payload = models.JSONField(null=True, blank=True)
    response_payload = models.JSONField(null=True, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    success = models.BooleanField(null=True)
    error_message = models.TextField(null=True, blank=True)
    order = models.ForeignKey('domain.Order', ...)
```

**Current Usage:** Defined but zero instantiation in:
- `src/application/providers/mock_nubefact_client.py` — No logging
- `src/application/providers/nubefact_client.py` — No logging
- `src/application/usecases/query_invoice_status.py` — No logging
- `src/domain/tasks/sync_invoice_tasks.py` — No logging

**Grep Result:** No `ExternalRequestLog.objects.create()` in invoice flow.

---

#### `InvoiceSyncQueue.last_response` (src/domain/models/invoicing.py)
**Status:** ✅ ACTIVELY PERSISTING PAYLOADS.

```python
class InvoiceSyncQueue(TenantModel):
    last_response = models.JSONField(null=True, blank=True)  # respuesta de Nubefact
    last_error = models.TextField(null=True, blank=True)      # error message (500 chars)
    last_attempt_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
```

**Data Flow:**
```
MockNubefactClient.get_invoice_status()
  ↓ returns { 'raw_response': {...}, 'accepted': bool, ... }
InvoiceStatusQueryUseCase.execute()
  ↓ result = provider.get_invoice_status(...)
  ↓ return result
sync_single_invoice_task() [line 168, 183]
  ↓ entry.last_response = result.get("raw_response")
  ↓ entry.save(update_fields=["last_response", ...])
```

**Payloads Stored:** Last response from SUNAT polling (JSON structure preserved).

**Example Payload in MockNubefactClient:**
```python
{
    'accepted': true/false,
    'observed': true/false,
    'rejected': true/false,
    'hash': 'CDR-HASH-...',
    'provider_reference': 'NUBEFACT-REF-...',
    'raw_response': {  # ← THIS IS PERSISTED
        'mock': True,
        'scenario': 'accepted',
        'external_id': '...'
    }
}
```

---

#### `OrderWorkflowLog.metadata` (src/domain/models/workflow_audit.py)
**Status:** ✅ STRUCTURED ERROR CAPTURE (optional).

```python
class OrderWorkflowLog(TenantModel):
    action = models.CharField(...)  # start, error, completed, etc.
    status = models.CharField(...)  # pending, processing, failed, completed
    metadata = models.JSONField(default=dict, blank=True)
```

**Data Flow:**
```
OrderWorkflowService._audit_log(order, 'error', 'failed', metadata={'error': str(e)})
  ↓ OrderWorkflowLog.objects.create(
      action='error',
      status='failed',
      metadata={'error': 'Network timeout: ...'}
    )
```

**Example Error Storage:**
```json
{
    "action": "error",
    "status": "failed",
    "metadata": {
        "error": "NubefactTemporaryError: Timeout"
    }
}
```

---

### 1.2 Payload Persistence Summary

| Model | Field | Type | Usage | Format |
|-------|-------|------|-------|--------|
| ExternalRequestLog | request_payload | JSONField | ❌ Never written | (unused) |
| ExternalRequestLog | response_payload | JSONField | ❌ Never written | (unused) |
| InvoiceSyncQueue | last_response | JSONField | ✅ Every poll | JSON object |
| OrderWorkflowLog | metadata | JSONField | ✅ On error | JSON object |

**Conclusion:** Payloads ARE persisted today via `InvoiceSyncQueue.last_response` and partially via `OrderWorkflowLog.metadata`. ExternalRequestLog model is orphaned (prepared but unused).

---

## 2. ERROR TAXONOMY DISCOVERY: Sources and Categorization

### 2.1 Error Sources in Current System

#### A. Task-Level Errors (sync_single_invoice_task)
**Location:** `src/domain/tasks/sync_invoice_tasks.py`

```python
try:
    result = InvoiceStatusQueryUseCase().execute(entry)
    # ...
except Exception as exc:
    logger.error(f"[invoice.poll.lock_failed]...{exc}")
    raise
```

Errors logged but NOT categorized.

**Current Error Recording:**
- Logs to stderr/stdout (ephemeral)
- `InvoiceSyncQueue.last_error` set via `entry.mark_exhausted("Max attempts reached...")`
- String message, no structure

#### B. UseCase-Level Errors (InvoiceStatusQueryUseCase)
**Location:** `src/application/usecases/query_invoice_status.py`

```python
if not order.invoice_external_id:
    raise NubefactPermanentError("order_id={order.id} no tiene invoice_external_id...")

try:
    config = CompanyInvoiceConfig.objects.get(organization=order.organization)
except CompanyInvoiceConfig.DoesNotExist:
    raise NubefactPermanentError("CompanyInvoiceConfig no encontrada...")
```

Errors raised as domain exceptions but not logged to audit trail.

#### C. Provider-Level Errors
**Location:** `src/application/providers/mock_nubefact_client.py`

```python
if scenario == 'timeout':
    raise NubefactTemporaryError(f"Mock timeout — external_id={external_id}")
if scenario == 'error':
    raise NubefactTemporaryError(f"Mock network error — external_id={external_id}")
```

Errors are exceptions but NOT caught or categorized at task level.

#### D. Workflow-Level Errors
**Location:** `src/application/services/order_workflow_service.py`

```python
except Exception as e:
    order.workflow_status = 'failed'
    self._audit_log(order, 'error', 'failed', metadata={'error': str(e)})
    raise
```

Errors ARE captured in `OrderWorkflowLog.metadata`.

---

### 2.2 Error Storage Locations

| Source | Storage | Category | Retention |
|--------|---------|----------|-----------|
| Task lock failure | stderr + logs | Operational | Ephemeral |
| UseCase exceptions | Raised to task | Business logic | Lost if task uncaught |
| Provider errors | Raised to UseCase | Network/API | Lost if UseCase uncaught |
| Workflow errors | OrderWorkflowLog.metadata | Business logic | ✅ Persistent |
| Sync exhaustion | InvoiceSyncQueue.last_error | Reconciliation | ✅ Persistent (500 chars) |

**Gap:** No structured error categorization. Current system:
- Logs errors as strings
- Cannot distinguish Temporary (503, timeout) vs Permanent (RUC inválido, falta documento)
- No error code/classification for future "Error Explorer"

---

### 2.3 Error Taxonomy Recommendation

For future "Error Explorer" to work, errors should be categorized:

**Proposed Categories:**
1. **TEMPORARY** — Retry-able (network 503/504, timeout)
2. **PERMANENT** — Config/data invalid (RUC inválido, missing fields)
3. **RATE_LIMITED** — Throttling (429 Too Many Requests)
4. **CREDENTIALS** — Auth failure (invalid token)
5. **CONFIGURATION** — Missing/invalid tenant setup

Currently NO structured taxonomy exists in code.

---

## 3. CORRELATION CANDIDATE: End-to-End Traceability

### 3.1 Order.id as Canonical Identifier

Order UUID propagates across the entire invoice lifecycle:

```
Order (created)
  ↓ order.id
  ↓
Order.status = PAID → OrderWorkflowService.handle_order_paid()
  ↓ order.id
  ↓
OrderWorkflowLog.order_id (audit trail)
  ↓ order.id
  ↓
create_invoice_task(order.id)
  ↓ order.id
  ↓
InvoiceSyncQueue.order_id (OneToOne)
  ↓ order.id
  ↓
sync_single_invoice_task(entry_id → entry.order_id)
  ↓ order.id
  ↓
InvoiceStatusQueryUseCase.execute(entry) → order.id implicit
  ↓ order.id
  ↓
Order.invoice_status updated + Order.invoice_hash set
  ↓ order.id
  ↓
AccountingEntry.order_id (OneToOne, when accepted)
```

**Evidence:**

1. **OrderWorkflowLog:**
   ```python
   OrderWorkflowLog.objects.filter(order_id=<order_id>).order_by('timestamp')
   ```
   ✅ Returns complete audit trail for one order.

2. **InvoiceSyncQueue:**
   ```python
   InvoiceSyncQueue.objects.get(order_id=<order_id>)
   ```
   ✅ Exactly one queue entry per order (OneToOne).

3. **AccountingEntry:**
   ```python
   AccountingEntry.objects.get(order_id=<order_id>)
   ```
   ✅ Exactly one entry per order (OneToOne, only when accepted).

4. **ExternalRequestLog** (if populated):
   ```python
   ExternalRequestLog.objects.filter(order_id=<order_id>)
   ```
   Currently empty but schema supports correlation.

### 3.2 Correlation Traceability Chain

**Today's Implementation:**
```
SELECT * FROM order WHERE id = 123
  ↓
SELECT * FROM order_workflow_log WHERE order_id = 123 ORDER BY timestamp
  ↓
SELECT * FROM invoice_sync_queue WHERE order_id = 123
  ↓
SELECT * FROM accounting_entry WHERE order_id = 123
```

**Unified Timeline Query:**
```sql
SELECT 
    'order_created' as event_type,
    order.created_at as timestamp,
    order.id as order_id,
    order.invoice_status as detail
FROM order WHERE order.id = 123

UNION ALL

SELECT 
    'workflow_event' as event_type,
    owf.timestamp,
    owf.order_id,
    owf.action
FROM order_workflow_log owf WHERE owf.order_id = 123

UNION ALL

SELECT 
    'sync_attempt' as event_type,
    isq.last_attempt_at,
    isq.order_id,
    CONCAT('Attempt ', isq.attempts, ' - ', isq.status)
FROM invoice_sync_queue isq WHERE isq.order_id = 123

UNION ALL

SELECT 
    'accounting' as event_type,
    ae.created_at,
    ae.order_id,
    ae.entry_type
FROM accounting_entry ae WHERE ae.order_id = 123

ORDER BY timestamp
```

**Result:** ✅ SUFFICIENT. Order.id is a valid canonical correlation identifier.

---

### 3.3 What IS Missing from Correlation

| Element | Current | Needed |
|---------|---------|--------|
| Order.id propagation | ✅ Complete | — |
| Request/response logging | ⚠️ Partial (only last_response in queue) | ExternalRequestLog usage |
| Error categorization | ❌ None | Taxonomy enum |
| Request UUID (Nubefact x-request-id) | ❌ Not captured | Should be added to ExternalRequestLog |
| Task ID (Celery) | ✅ In logs via self.request.id | ✅ But not in DB |
| Distributed trace headers | ❌ None | Deferred to Sprint 5 |

---

## 4. RECOMMENDATIONS

### 4.1 Short Term (No Schema Changes Required)

1. **Start Using ExternalRequestLog**
   - Call `ExternalRequestLog.objects.create()` in `InvoiceStatusQueryUseCase.execute()` or at task level
   - Populate `request_payload`, `response_payload`, `status_code`, `duration_ms`, `success`, `error_message`
   - This unifies all external API calls in one model (currently orphaned)

2. **Enrich OrderWorkflowLog.metadata**
   - Add error classification: `metadata = {'error_type': 'TEMPORARY|PERMANENT|...', 'message': '...'}`
   - Add request/response summaries when available

3. **Backfill InvoiceSyncQueue.last_error with structured data**
   - Currently: `last_error = "Max attempts reached"`
   - Proposed: `last_error = "PERMANENT: RUC inválido (SUNAT)"`

### 4.2 Medium Term (Schema Evolution, Sprint 5+)

1. **Add ExternalRequestLog.request_id field**
   - Store Nubefact's x-request-id or Celery task_id for distributed tracing

2. **Add error_type enum to InvoiceSyncQueue or create ErrorLog model**
   - Structure error categories for "Error Explorer" dashboard

3. **Implement correlation trace context**
   - Use OpenTelemetry or similar for cross-boundary correlation IDs

### 4.3 For FASE 3.4 Implementation (Next)

If building an "Invoice Explorer" or "Error Explorer" dashboard:
- DO use Order.id as the primary query key (✅ canonical, exists everywhere)
- DO aggregate OrderWorkflowLog + InvoiceSyncQueue + AccountingEntry via Order.id
- DO NOT rely on ExternalRequestLog until populated (currently orphaned)
- DO add request ID capture to ExternalRequestLog before production use

---

## 5. AUDIT FINDINGS: Table Summary

### Current State

| Dimension | Finding | Evidence | Risk |
|-----------|---------|----------|------|
| **Payload Persistence** | Partial — via InvoiceSyncQueue.last_response | ✅ `last_response` JSON saved | Medium: ExternalRequestLog unused |
| **Error Recording** | Implicit, scattered, non-structured | ⚠️ String logs + metadata dict | Medium: Hard to query, categorize |
| **Correlation** | Order.id sufficient | ✅ OneToOne/FK throughout | Low: Coherent tracing possible |
| **Request Logging** | Model exists but never populated | ❌ Zero ExternalRequestLog writes | Medium: Orphaned infrastructure |
| **Observability Gaps** | No request IDs, no error taxonomy | ❌ Not captured | Medium: No distributed tracing |

---

## 6. Conclusion

**Nexus OMS has a functional but fragmented observability layer.**

✅ **What Works:**
- Payloads persist in InvoiceSyncQueue.last_response
- Order.id correlates consistently across models
- Audit trail via OrderWorkflowLog.metadata exists
- Schema supports full observability (ExternalRequestLog ready)

❌ **What Doesn't:**
- ExternalRequestLog is orphaned (defined but never used)
- No structured error taxonomy (all errors are strings)
- No request IDs for distributed tracing
- No automated error discovery mechanism

**Next Step:** For Sprint 5 observability enhancements, populate ExternalRequestLog and add error taxonomies to unlock the full potential of existing infrastructure.

---

**Audited by:** Technical Lead Audit  
**Verification:** Code inspection + model schema review  
**No Breaking Changes:** This audit is read-only.
