# S0.5: Data Classification Audit

**Date**: 2026-06-19  
**Status**: Complete  
**Scope**: Sensitivity Classification of All Models & Fields

---

## Executive Summary

Nexus OMS manages 4 sensitivity tiers:

- **Public**: Non-sensitive reference data (Categories, Suppliers)
- **Internal**: Business data visible within organization (Products, Warehouses)
- **Confidential**: Customer + financial data requiring strong isolation (Orders, Payments, Reports)
- **Sensitive**: Auth credentials + PII requiring encryption + masking (API Keys, Tokens, Emails)

---

## Classification Matrix

### Public (No RLS Required)

| Model | Sensitivity | Data Examples | RLS | Masking | Comments |
|-------|------------|---------------|----|---------|----------|
| **Category** | Public | name, description | No | No | Reference data; shared catalog ok |
| **ExchangeRate** | Public | date, buy_price, sell_price | No | No | Global financial data; public rates |

---

### Internal (RLS Recommended)

| Model | Sensitivity | Data Examples | RLS | Masking | Comments |
|-------|------------|---------------|----|---------|----------|
| **Supplier** | Internal | name, RUC, email, phone | Yes | Email/Phone | Business contact; sensitive if disclosed |
| **Warehouse** | Internal | name, address | Yes | Address | Operational location; security risk if public |
| **Stock** | Internal | quantity, updated_at | Yes | Quantity | Inventory levels; competitive intelligence |
| **StockMovement** | Internal | type, reason, quantity | Yes | Qty trends | Supply chain data; operational visibility |
| **TaxConfiguration** | Internal | name, rate | Yes | No | Tax rules; org-specific compliance |
| **CashReconciliation** | Internal | expected, actual, difference | Yes | Amounts | Financial record; internal only |
| **CompanyInvoiceConfig** | Internal | api_url, enabled, provider | Yes | Token redacted | Invoice endpoint; sensitive config |
| **ExternalServiceConfig** | Internal | provider, base_url, timeout | Yes | **api_key, api_secret REDACTED** | Credentials stored; **CRITICAL masking** |
| **PurchaseOrder** | Internal | total_cost, status | Yes | Cost | Procurement records; supplier negotiations |
| **PurchaseOrderItem** | Internal | unit_cost, quantity | Yes | Cost | Unit pricing; competitive data |

---

### Confidential (RLS + Encryption Recommended)

| Model | Sensitivity | Data Examples | RLS | Masking | Comments |
|-------|------------|---------------|----|---------|----------|
| **Client** | Confidential | name, email, phone, address, document_number | Yes | **All PII** | Customer database; GDPR-critical |
| **Product** | Confidential | name, price, SKU | Yes | Price (maybe) | Pricing strategy; competitive data |
| **Order** | Confidential | customer_name, customer_email, delivery_address, total, subtotal, tax | Yes | **Email, address, amounts** | Full customer transaction; ultra-sensitive |
| **OrderItem** | Confidential | price_at_order, quantity | Yes | Amounts | Derived from Order; inherit sensitivity |
| **OrderReturn** | Confidential | reason, refund_amount, notes | Yes | Amounts, notes | Customer complaints; sensitive feedback |
| **Payment** | Confidential | method, amount, fee, transaction_ref | Yes | **Amount, transaction_ref** | Payment data; PCI-DSS concern |
| **SalesReport** | Confidential | total_sales, order_count, data (JSON) | Yes | All aggregates | Financial summaries; P&L data |
| **AccountingEntry** | Confidential | amount_gross, amount_tax, amount_net | Yes | All amounts | Accounting records; audit trail |
| **AccountingEntryLine** | Confidential | debit, credit, account_code | Yes | All amounts | Sub-ledger; compliance audit |
| **OrderWorkflowLog** | Confidential | metadata (errors, retries) | Yes | Conditional | Order-linked audit; errors may expose issues |

---

### Sensitive (RLS + Encryption + Access Control Required)

| Model | Sensitivity | Data Examples | RLS | Masking | Comments |
|-------|------------|---------------|----|---------|----------|
| **CustomUser** | Sensitive | email, password_hash, organization_fk | Yes | **Email hash, password** | Auth credentials; never log in full |
| **ExternalRequestLog** | Sensitive | request_payload, response_payload, error_message | Yes | **Sanitize tokens, keys** | Third-party integrations; may contain secrets |
| **InvoiceSyncQueue** | Sensitive (Mixed) | response_payload, last_error | Yes | **Tokens, errors with sensitive data** | Invoice cycle; error messages may expose paths |

---

## Detailed Sensitivity Rationale

### Client (Confidential → Sensitive PII)

```json
{
  "document_type": "DNI",           // PII identifier type
  "document_number": "12345678",    // ← PII: unique person identifier
  "name": "Juan Pérez García",      // ← PII: personal name
  "address": "Av. Lima 123, Lima",  // ← PII: location
  "email": "juan@example.com",      // ← PII: contact email
  "phone": "+51987654321"           // ← PII: phone number
}
```

**Classification**: SENSITIVE PII  
**Why**: Identifiable personal information; GDPR/CCPA applies  
**RLS**: Required (organization isolation essential)  
**Masking**: YES — logs should never contain full document_number, email, phone  
**Encryption**: Optional but recommended at-rest

---

### Order (Confidential)

```json
{
  "customer_name": "Corp A Ltd.",      // Business name (semi-public)
  "customer_email": "buyer@corpa.com", // ← PII: email
  "delivery_address": "...",           // ← PII: location
  "subtotal": 5000.00,                 // ← Financial: sensitive
  "tax_amount": 900.00,                // ← Financial
  "total_amount": 5900.00,             // ← Financial: ultra-sensitive
  "shipping_fee": 50.00,               // ← Competitive: pricing strategy
  "invoice_status": "accepted",        // ← Operational; log OK
  "invoice_hash": "abc123...",         // ← Non-sensitive audit trail
}
```

**Classification**: CONFIDENTIAL + PII  
**Why**: Customer transaction record; amounts reveal business volumes and margins  
**RLS**: Required  
**Masking**: YES — email, address, amounts in logs  
**Encryption**: Optional but recommended; consider at-rest encryption for orders table

---

### ExternalServiceConfig (Sensitive Credentials)

```json
{
  "provider_name": "nubefact",       // Non-sensitive
  "environment": "production",        // Non-sensitive
  "base_url": "https://api.nubefact.com",  // Low sensitivity
  "api_key": "sk_prod_xxxxx",        // ← SENSITIVE: secret
  "api_secret": "secret_xxxxx",      // ← SENSITIVE: secret
  "timeout_seconds": 15,             // Non-sensitive
  "notes": "Primary invoice provider" // Non-sensitive
}
```

**Classification**: SENSITIVE (Credentials)  
**Why**: api_key + api_secret are credentials; if leaked, attacker can call external APIs on behalf of org  
**RLS**: Required  
**Masking**: YES — Always mask api_key and api_secret in logs and error messages  
**Encryption**: REQUIRED at-rest (encrypt these fields in DB)  
**Access Control**: Only ADMIN users should see full credentials (show masked in logs)

---

### ExternalRequestLog (Sensitive + Potentially Infected)

```json
{
  "provider_name": "nubefact",       // Non-sensitive
  "operation": "create_invoice",     // Non-sensitive
  "request_payload": {               // ← POTENTIALLY SENSITIVE
    "api_key": "sk_prod_xxxxx",      // ← If sent in request, contains secret!
    "invoice_data": {
      "customer_name": "Corp A",
      "customer_email": "buyer@corpa.com",  // ← PII if captured
    }
  },
  "response_payload": {              // ← MAY CONTAIN SECRETS
    "invoice_id": "INV-001",
    "error": "Invalid API key format"  // ← May expose internal logic
  },
  "error_message": "Connection timeout at /api/invoices/create"  // ← Exposes internal paths
}
```

**Classification**: SENSITIVE (Audit logs + potential secrets + PII)  
**Why**: May contain credentials, PII, and stack traces if captured  
**RLS**: Required  
**Masking**: YES — Redact api_key, email, phone from payloads; redact stack traces from errors  
**Logging Policy**: Do NOT log full request/response; log only operation + result code  
**Encryption**: Optional; not credentials directly, but may contain them

---

## Masking Requirements

### Fields Requiring Masking in Logs

| Field | Model | Mask Strategy | Example |
|-------|-------|---------------|---------|
| `api_key` | ExternalServiceConfig | Show only last 4 chars | `sk_prod_**XX` |
| `api_secret` | ExternalServiceConfig | Redact entirely | `[REDACTED]` |
| `password_hash` | CustomUser | Never log | `[REDACTED]` |
| `email` | CustomUser, Client, Order | Hash or mask domain | `juan@ex\*\*` or hash |
| `phone` | Client, Order | Show only last 4 digits | `+51\*\*\*\*4321` |
| `document_number` | Client | Show only last 4 digits | `1234\*\*\*\*` |
| `delivery_address` | Order | Show only city/country | `Lima, Peru` |
| `customer_email` | Order | Mask as Client.email | `buyer@co\*\*` |
| `amount` fields | Order, Payment, AccountingEntry | Round to nearest 100 | `5,900.00` → `5,900` |
| `transaction_reference` | Payment | Show only last 4 | `\*\*\*\*3456` |
| `response_payload` (full JSON) | ExternalRequestLog | Log only structure + status | `{"status": 200, "duration_ms": 45}` |

---

## RLS Enforcement by Tier

| Tier | Current Enforcement | RLS Status | Priority |
|------|-------------------|-----------|----------|
| Public | None (global) | ❌ Not needed | Low |
| Internal | TenantManager | ✅ Recommended (S1) | Medium |
| Confidential | TenantManager | ✅ Required (S1) | HIGH |
| Sensitive | TenantManager + Masking | ✅ Required (S1) + Encryption (S2) | CRITICAL |

---

## Compliance Mapping

### GDPR (Personal Data)

Models capturing personal data:
- ✅ **Client** (document, name, email, phone, address)
- ✅ **Order** (customer name, email, address)
- ✅ **CustomUser** (email, organization)
- ✅ **ExternalRequestLog** (if PII captured in payloads)

**Required Controls**:
- ✅ RLS (data isolation by org)
- ✅ Masking in logs
- ✅ Audit trail (who accessed)
- ✅ Encryption at-rest (optional but recommended)

---

### SOC2 Trust Services

**Confidentiality (CC)**: Sensitive + Confidential models  
**Integrity (CI)**: All models (but especially Accounting entries)  
**Availability (A)**: Critical for Order + Payment models

**Current State**: PARTIAL (TenantManager provides logical controls)  
**Target (S2)**: STRONG (RLS + encryption + audit)

---

## Recommendation

**S1 Priorities**:
1. ✅ Implement masking for Sensitive fields in all logs
2. ✅ Enforce RLS on Confidential + Sensitive models
3. ✅ Add audit logging for who accessed Sensitive fields
4. ⏸️ Encryption at-rest deferred to S2

**S2 Priorities**:
1. 🔐 Field-level encryption for api_key, api_secret in ExternalServiceConfig
2. 🔐 At-rest encryption for Order, Payment, Client tables
3. 🔐 Audit trail logging with Sensitive field access tracking

---

## References

- [GDPR: Personal Data Definition](https://gdpr-info.eu/art-4-gdpr/)
- [OWASP: Data Classification](https://owasp.org/www-community/attacks/Taxonomy_of_Data_Classification_Types)
- [SOC2 Trust Services Criteria](https://www.aicpa.org/content/dam/aicpa/research/standards/auditattest/downloadabledocuments/trust-services-criteria.pdf)
