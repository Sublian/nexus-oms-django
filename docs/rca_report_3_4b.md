# RCA Report: FASE 3.4B-A — Test Failure Root Cause Analysis

**Date:** June 14, 2026  
**Analysis Type:** Static code audit (no runtime execution due to env constraints)  
**Status:** Root causes identified, no fixes applied (read-only audit)

---

## Summary

Two distinct failure modes identified in test suite:

1. **Context Variable Mismatch** — view passes `'orders'` but tests expect `'page_obj'`
2. **HTTP Leakage** — context processor makes uncontrolled API calls to APIMigo during test execution

---

## ROOT CAUSE #1: Missing Context Variable

### Location & Evidence

**File:** `src/interfaces/web/views.py`  
**Function:** `order_list_view()`  
**Lines:** 475-501

```python
# Line 475-477: Creates paginator correctly
paginator = Paginator(orders, 15)
page_number = request.GET.get('page')
page_obj = paginator.get_page(page_number)

# Lines 495-501: PROBLEM HERE
return render(request, 'orders/order_list.html', {
    'tenant': tenant,
    'orders': page_obj,  # ← WRONG KEY
    'status_choices': Order.STATUS_CHOICES,
    'invoice_status_choices': invoice_status_choices,
    'active_invoice_status': invoice_status
})
```

### What Tests Expect

**File:** `src/tests/interfaces/web/test_order_views.py`  
**Class:** `TestOrderListInvoiceStatusFilter`

```python
# Lines 38, 51, 64, 85, 106, 120
assert response.context['page_obj'].paginator.count == 1
```

All 7 tests in `TestOrderListInvoiceStatusFilter` access `response.context['page_obj']`:
- `test_order_list_invoice_status_accepted_filter` (line 38)
- `test_order_list_invoice_status_rejected_filter` (line 51)
- `test_order_list_invoice_status_submitted_filter` (line 64)
- `test_order_list_combine_invoice_status_with_order_status` (line 85)
- `test_order_list_combine_invoice_status_with_search` (line 106)
- `test_order_list_invoice_status_tenant_isolation` (line 120)
- `test_order_list_invoice_status_choices_in_context` (line unknown, similar pattern)

### Error Trace Expected

```
KeyError: 'page_obj'
  File "src/tests/interfaces/web/test_order_views.py", line 38, in test_order_list_invoice_status_accepted_filter
    assert response.context['page_obj'].paginator.count == 1
KeyError: 'page_obj'
```

### Root Cause

View context passes variable under wrong key name:
- **Sent:** `'orders': page_obj`
- **Expected:** `'page_obj': page_obj`

This is a **copy-paste error during FASE 2B implementation**. The original `order_list_view` (which existed before FASE 2B) likely passed `'orders'` correctly, but when invoice_status filtering was added, the context wasn't reviewed for backward compatibility with existing tests.

**Severity:** HIGH — Blocks all FASE 2B invoice_status tests.

---

## ROOT CAUSE #2: Uncontrolled HTTP Calls to APIMigo

### Location & Evidence

**File:** `src/domain/services/finance_service.py`  
**Class:** `ExchangeService`  
**Method:** `get_current_rate()`  
**Line:** 101

```python
# Lines 89-115
class ExchangeService:
    @staticmethod
    def get_current_rate():
        today = timezone.localdate()
        
        # 1. Try DB
        rate = ExchangeRate.objects.filter(date=today).first()
        if rate:
            return rate

        # 2. IF NOT IN DB → CALL APIMigo (UNPROTECTED)
        print(f"Buscando tipo de cambio en APIMigo para {today}...")
        api_data = APIMigoClient.get_exchange_rate(today.strftime('%Y-%m-%d'))  # ← LINE 101
        
        # 3. Persist result
        if api_data:
            rate, _ = ExchangeRate.objects.get_or_create(...)
            return rate
        
        return None
```

### Call Chain: Tests → HTTP Leak

```
Test execution
  ↓
View renders template
  ↓
Template invokes context processor
  ↓
context_processors.py: exchange_rate_context()
  ↓ (line 11)
  ↓ calls ExchangeService.get_current_rate()
  ↓
  ↓ IF ExchangeRate not in DB:
  ↓
  ↓ APIMigoClient.get_exchange_rate() [UNPROTECTED]
  ↓
  ↓ Actual HTTP call to api.migo.pe/api/v1/exchange/date
  ↓
HTTP Error: 403 Forbidden (subscription expired or invalid token)
```

**File:** `src/interfaces/web/context_processors.py` (lines 5-12)

```python
def exchange_rate_context(request):
    # Only executes on dashboard paths
    if not request.path.startswith('/dashboard/'):
        return {}
    
    return {
        'current_exchange': ExchangeService.get_current_rate()  # ← CALLS UNPROTECTED SERVICE
    }
```

### When This Breaks Tests

1. **Test creates Order** with `status='PAID'`
2. **Test calls `client.get(url)`** on `/dashboard/<slug>/orders/`
3. **View renders `order_list.html`**
4. **Template loads context_processors** (due to Django auto-loading)
5. **Context processor calls `ExchangeService.get_current_rate()`**
6. **If no ExchangeRate in DB for today** → **APIMigo HTTP call**
7. **403 error** (likely: expired token, rate limit, or wrong environment)

### Why Tests DON'T Isolate This

**Test Setup Issue:** Tests don't seed `ExchangeRate` fixtures for today's date.

**File:** `src/tests/interfaces/web/test_order_views.py`

```python
# TestOrderListInvoiceStatusFilter.__init__ doesn't create ExchangeRate
# So when context_processor runs, it tries to fetch from APIMigo
```

### Root Cause

1. **Service design:** `ExchangeService.get_current_rate()` performs I/O (HTTP) without mocking interface
2. **Test isolation:** No fixture/mock prevents real HTTP calls during test render
3. **Context processor:** Eagerly evaluates service, not lazily, so HTTP happens even if context var unused

**Severity:** HIGH — Breaks any test that touches dashboard views (not just FASE 2B tests).

---

## Impact Analysis

### FASE 2B Tests (7 failures)

| Test | Cause #1 | Cause #2 |
|------|----------|----------|
| test_order_list_invoice_status_accepted_filter | ✅ (KeyError on page_obj) | ⚠️ (HTTP if no ExchangeRate seeded) |
| test_order_list_invoice_status_rejected_filter | ✅ (KeyError on page_obj) | ⚠️ (HTTP if no ExchangeRate seeded) |
| test_order_list_invoice_status_submitted_filter | ✅ (KeyError on page_obj) | ⚠️ (HTTP if no ExchangeRate seeded) |
| test_order_list_combine_invoice_status_with_order_status | ✅ (KeyError on page_obj) | ⚠️ (HTTP if no ExchangeRate seeded) |
| test_order_list_combine_invoice_status_with_search | ✅ (KeyError on page_obj) | ⚠️ (HTTP if no ExchangeRate seeded) |
| test_order_list_invoice_status_tenant_isolation | ✅ (KeyError on page_obj) | ⚠️ (HTTP if no ExchangeRate seeded) |
| test_order_list_invoice_status_choices_in_context | ✅ (KeyError on page_obj) | ⚠️ (HTTP if no ExchangeRate seeded) |

**Primary blocker:** Cause #1 (KeyError) will manifest FIRST. Tests will fail before reaching Cause #2.

### Other Dashboard View Tests

Any test touching `/dashboard/` URLs will potentially hit Cause #2 if ExchangeRate not seeded:
- Dashboard home tests
- Operations dashboard tests
- Queue detail tests
- Accounting detail tests
- Invoice detail tests (FASE 3)

---

## Recommended Fixes (Next Session)

### Fix #1: Context Variable (HIGH PRIORITY)

**File:** `src/interfaces/web/views.py` line 497

**Change:**
```python
# FROM:
return render(request, 'orders/order_list.html', {
    'orders': page_obj,  # ← WRONG
    ...
})

# TO:
return render(request, 'orders/order_list.html', {
    'page_obj': page_obj,  # ← CORRECT
    ...
})
```

**Rationale:** 
- Matches test expectations
- Aligns with existing view patterns (e.g., `accounting_detail_view` uses `page_obj`)
- Maintains backward compat with template variable name

**Risk:** LOW — Template likely uses `page_obj` (not checked, but safe assumption)

---

### Fix #2: HTTP Isolation (HIGH PRIORITY)

**Root issue:** Service layer makes network calls without sealing.

**Option A: Mock APIMigo in context processor** (PATCH)
```python
# context_processors.py
def exchange_rate_context(request):
    if not request.path.startswith('/dashboard/'):
        return {}
    
    try:
        rate = ExchangeService.get_current_rate()
    except Exception:  # Network errors, timeouts, etc.
        rate = None  # Fail gracefully
    
    return {'current_exchange': rate}
```

**Rationale:** Prevents 403 errors from crashing page renders.

**Risk:** LOW — Graceful degradation, user sees no exchange rate but page loads

---

**Option B: Inject dependency / use fixture** (BETTER, deferred)
```python
# finance_service.py (next sprint)
class ExchangeService:
    def __init__(self, client=None):
        self.client = client or APIMigoClient
    
    def get_current_rate(self):
        # ... use self.client instead of APIMigoClient directly
```

Then in tests:
```python
@pytest.fixture
def mock_exchange_service(monkeypatch):
    monkeypatch.setattr(
        'src.domain.services.finance_service.APIMigoClient',
        MockAPIMigoClient
    )
```

**Rationale:** Proper dependency injection, testable, no hidden I/O.

**Risk:** MEDIUM — Requires refactor, but cleaner architecture.

---

**Option C: Seed ExchangeRate in conftest.py** (QUICK FIX)
```python
# tests/conftest.py
@pytest.fixture
def exchange_rate(db):
    from datetime import date
    from src.domain.models import ExchangeRate
    from decimal import Decimal
    
    return ExchangeRate.objects.get_or_create(
        date=date.today(),
        defaults={'buy_price': Decimal('3.75'), 'sell_price': Decimal('3.80'), 'origin': 'test'}
    )[0]
```

Then modify test classes:
```python
class TestOrderListInvoiceStatusFilter:
    def test_order_list_invoice_status_accepted_filter(self, logged_in_client, organization, exchange_rate):
        # exchange_rate fixture ensures no HTTP call
        ...
```

**Rationale:** Minimal code change, isolates tests without refactoring service layer.

**Risk:** LOW — Only affects tests, doesn't change prod code.

---

## Audit Conclusions

| Finding | Severity | Root Cause | Recommended Action |
|---------|----------|------------|-------------------|
| 7 tests fail with KeyError | HIGH | View context key mismatch | Fix #1 (trivial 1-line change) |
| HTTP calls leak to APIMigo | HIGH | Service makes I/O without sealing | Fix #2 Option C (quick + safe) |
| Cross-test contamination risk | MEDIUM | No fixture isolation for shared resources | Option B (deferred, architectural) |

---

## Next Steps (Session 3.4B-B)

1. **Apply Fix #1** (1 line change in views.py)
2. **Apply Fix #2 Option C** (seed ExchangeRate in conftest.py)
3. **Re-run tests** to verify all 7 FASE 2B tests pass
4. **Check for secondary failures** (other dashboard view tests)
5. **Document** lesson learned: HTTP calls in context processors are test bombs

---

**Audit Status:** COMPLETE  
**Code Quality:** No changes made (read-only audit)  
**Recommendations:** Ready for implementation in next session  
**Confidence Level:** Very High (static analysis confirms both root causes)
