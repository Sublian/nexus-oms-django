# 🗺️ Roadmap Fase 2: Operabilidad Real + Nubefact

## 📋 Unificación: guia3.md (Bloques pendientes) + guia4.md (Nubefact específico)

---

## 📊 Estado Actual (Fin Sesión 1)

| Componente | Status | Evidencia |
|---|---|---|
| Resiliencia (try/except) | ✅ Done | Bloque 1 guia3 |
| Aislamiento (UseCase) | ✅ Done | Bloque 2 guia3 |
| Auditoría persistente | ✅ Done | Bloque 5 guia3 |
| **Async (Celery)** | 🔜 Pending | Bloque 3 guia3 + Bloque 6 guia4 |
| **Retry automático** | 🔜 Pending | Bloque 4 guia3 + Bloque 7 guia4 |
| **Nubefact integration** | 🔜 Pending | Bloque 6 guia3 + Bloques 2-4, 5 guia4 |

---

## 🎯 MAPA DE IMPLEMENTACIÓN UNIFICADO

### FASE 2.1: Configuración Tenant-Aware (Sprint 1)

**guia4.md Bloque 1**: CompanyInvoiceConfig
```python
class CompanyInvoiceConfig(models.Model):
    company = models.OneToOneField(Organization)
    api_base_url = models.URLField()
    endpoint_url = models.CharField(max_length=255)
    token = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
```

**Razón crítica**: Cada tenant factura con su endpoint aislado (no singleton global)

---

### FASE 2.2: Provider Architecture (Sprint 1)

**guia4.md Bloques 2-4**: Interface + Mock + Client

```
InvoiceProvider (ABC)
  ├─ MockNubefactClient (desarrollo sin credenciales)
  └─ NubefactClient (producción)

Factory pattern:
  get_invoice_provider(config) → Mock | Nubefact
```

**CreateInvoiceUseCase** (guia4.md Bloque 5)
- Resolver tenant → config → provider → execute
- Persistir resultado (invoice_status, invoice_external_id)

---

### FASE 2.3: Async + Retry (Sprints 2-3)

**guia3.md Bloque 3 + guia4.md Bloque 6**: Celery Integration

```python
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=5
)
def create_invoice_task(self, order_id):
    order = Order.objects.get(id=order_id)
    CreateInvoiceUseCase().execute(order)

# En workflow:
def _trigger_invoicing(self, order):
    create_invoice_task.delay(order.id)
```

**Retry exponencial**: 1m → 2m → 4m → 8m → 16m

---

### FASE 2.4: Failure Strategy (Sprint 3)

**guia3.md Bloque 4 + guia4.md Bloque 7**: Exception hierarchy

```python
class NubefactTemporaryError(Exception):
    # timeout, 502, 503 → retry
    pass

class NubefactPermanentError(Exception):
    # 400, auth error, invalid payload → no retry
    pass
```

**En task**:
```python
except NubefactTemporaryError:
    raise self.retry(exc=exc)  # Celery retry

except NubefactPermanentError:
    order.invoice_status = "failed"
    order.save()
    # No retry
```

---

### FASE 2.5: Nubefact Real (Sprint 4)

**guia4.md Bloques 3, 8**: NubefactClient implementation

```python
class NubefactClient(InvoiceProvider):
    @property
    def endpoint(self):
        return f"{self.config.api_base_url}/{self.config.endpoint_url}"
    
    def create_invoice(self, order):
        payload = self._build_payload(order)
        response = self.session.post(
            self.endpoint,
            headers={"Authorization": self.config.token},
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        return response.json()

    def _build_payload(self, order):
        # Construir payload Nubefact
        pass
```

---

## 🧾 Testing Plan (guia4.md Bloque 9)

### Unit Tests
- CreateInvoiceUseCase
  - Config encontrada ✅
  - Config faltante ❌
  - Provider error handling ❌

### Integration Tests
- MockNubefact en Celery
  - order.invoice_status == "issued" ✅
  - invoice_external_id.startswith("MOCK") ✅
- Retry logic
  - Temporal error → retry ✅
  - Permanent error → no retry ✅

---

## 🎯 Orden de Implementación (guia4.md)

```
Sprint 1
├─ CompanyInvoiceConfig
├─ InvoiceProvider (ABC)
├─ MockNubefactClient
└─ CreateInvoiceUseCase

Sprint 2
├─ Celery task setup
└─ Workflow integration (_trigger_invoicing async)

Sprint 3
├─ Retry strategy
├─ Exception hierarchy
└─ Failure handling

Sprint 4
├─ NubefactClient real
├─ Payload builder
└─ Production tests
```

---

## ⚠️ INSIGHT CRÍTICO (guia4.md)

El punto más delicado NO es Celery ni Nubefact.

Es esto:
```
Resolver correctamente: tenant → provider → endpoint dinámico
```

**Si esto queda mal**:
- ❌ Facturas emitidas por empresa equivocada
- ❌ Contaminación entre tenants
- ❌ Bugs imposibles de rastrear

**Arquitectura correcta**:
```
Order (tenant-aware) 
  → CompanyInvoiceConfig (por tenant)
  → Provider Factory (dinámico por config)
  → NubefactClient(config) (endpoint único por tenant)
```

---

## 🧪 Métricas de Éxito Finales (guia4.md)

- ✅ Orden pagada dispara emisión async
- ✅ Cada tenant usa su endpoint correcto
- ✅ Si Nubefact cae, hay retry automático
- ✅ Todo corre sin credenciales (mock mode)
- ✅ Workflow principal permanece intacto

---

## 📅 Timeline Estimado

| Sprint | Duración | Objetivo |
|---|---|---|
| 1 | 1 sesión | Config + Providers + UseCase |
| 2 | 1 sesión | Celery + workflow async |
| 3 | 1 sesión | Retry + exception handling |
| 4 | 1 sesión | Nubefact real + producción |

**Total**: ~4 sesiones para Fase 2 completa

---

## 🚀 Siguiente Sesión

### Prioridades (orden):
1. **CompanyInvoiceConfig** model + migration
2. **InvoiceProvider** ABC interface
3. **MockNubefactClient** implementation
4. **CreateInvoiceUseCase** actualized con config resolution
5. Tests (mock flujo end-to-end)

### No hagas en siguiente sesión:
- ❌ Celery task setup (viene después)
- ❌ Nubefact real (necesita Sprint 4)
- ❌ Exception hierarchy avanzada (Sprint 3)

---

## 📌 Recap Estado Final (Sesión 1)

**Completado**:
- ✅ Fase 1: Control del flujo (100/100)
- ✅ Fase 1.5: Hardening (100/100)
- ✅ Fase 2 Bloques 1, 2, 5: Resiliencia, aislamiento, auditoría

**Tests**: 14/14 pass ✅

**Sistema**: Confiable → Resiliente → Aislado → Observable

**Próximo**: Async + Nubefact real (Fase 2 Sprints 1-4)
