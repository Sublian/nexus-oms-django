# Security Root — Nexus OMS Defense Roadmap

## ¿Qué es?

Roadmap de hardening de seguridad en **3 sectores**: S0 (Foundation), S1 (Tenant Isolation), S2 (PostgreSQL RLS).

```
SECURITY ROADMAP:
S0 (Complete)  →  S1 (✅ DONE: 337 tests)  →  S2 (Planned)
Foundation         Tenant Isolation           Row-Level Security
```

## Sector S0 — Foundation (Completado)

**Qué**: Base de seguridad (autenticación, autorización, thread-local cleanup).

**Checklist**:
- ✅ Custom user model `CustomUser` (email como USERNAME_FIELD)
- ✅ JWT + sessions auth implementados
- ✅ Thread-local context para tenant per request
- ✅ Middleware cleanup obligatorio

**Invariantes S0**:
```
1. AUTENTICACIÓN: Toda request debe pasar por auth
2. THREAD CLEANUP: OrganizationMiddleware limpia thread-local
3. TENANT CONTEXT: Middleware setea antes de cualquier query
```

---

## Sector S1 — Tenant Isolation Hardening (✅ COMPLETADO)

**Qué**: Sello de 4 fugas críticas de tenant via 3 opciones de defensa.

**Fugas Identificadas**:
1. **ViewSet Bypass** — Algunos viewsets no validaban tenant
2. **Global Bypass Inventory** — Código legacy que usaba `.all_objects`
3. **Superuser Context Gap** — Superuser sin `X-Org-ID` header exponía cross-tenant
4. **Mixin Inconsistency** — TenantViewMixin no centralizado

**Opciones de Defensa Implementadas**:

### Option A: Mixin Inspection (S1.1)
- Auditar todos los viewsets
- Verificar herencia de `TenantViewMixin`
- ✅ Completado

### Option B: Global Bypass Inventory (S1.2)
- Inventariar todas las instancias de `.all_objects`
- Documentar cada una (admin, migration, test)
- ✅ Documentado en audit log

### Option C: Centralized Enforcement (S1.3) — **ELEGIDA**
- Forzar todos los viewsets a heredar de `TenantViewMixin`
- Centralizar `get_organization()` con fallback seguro
- Sellar bypasss via validación en modelo
- ✅ Implementado + 337 tests en verde

**Resultado S1**:
- 0 ViewSets sin TenantViewMixin
- 0 Orphaned `.all_objects` calls
- Superuser context manejado explícitamente
- Garantía: Aislación de tenant en API + Web

---

## Sector S2 — Row-Level Security (Planificado)

**Qué**: Hardening adicional via PostgreSQL RLS + audit log + rate limiting.

**Objetivos**:
- Implementar RLS en órdenes críticas (prevent pg_superuser bypass)
- Audit trail para compliance (logging de accesos cross-tenant)
- Rate limiting en endpoints sensibles
- Circuit breaker para APIMigo (resiliencia)

**Fases S2.X**:
- **S2.0** (EN PROGRESO): Knowledge Graph Foundation ← Estás aquí
- **S2.1** (Próximo): RLS policy design + DDL
- **S2.2**: Audit logging implementation
- **S2.3**: Rate limiting + circuit breakers

---

## Invariantes Críticas de Seguridad

```
TENANT ISOLATION:
├─ Nunca .all_objects en código de negocio
├─ TenantManager filtra automáticamente
├─ Thread-local DEBE limpiarse post-request
├─ X-Org-ID header requerido para superuser
└─ Todas las querys van a través de TenantManager

INVOICE DEDUPLICATION:
├─ select_for_update() al inicio
├─ Check invoice_external_id (fast path)
├─ Check status 'processing' (otro worker in flight)
└─ Perder guardia = facturas duplicadas en SUNAT

WORKFLOW ATOMICITY:
├─ order.workflow_processed es canonical
├─ select_for_update() en claim lock
└─ Idempotencia garantizada
```

## ¿Por qué S1 antes que S2?

**Decisión**: Completar S1 (aislación en aplicación) ANTES de S2 (aislación en DB).

**Razón**: 
1. Application guards son más rápidos de implementar (no requieren downtime)
2. Defensa en profundidad: capas múltiples reducen riesgo de single point of failure
3. S2 (RLS) requiere testing más cuidadoso en producción
4. S1 da time-to-market ahora; S2 mejora futura

[Ver ADR-001](../decisions/ADR-001.md)

## Relaciones

- [Project](../project/root.md) — Roadmap general
- [Architecture](../architecture/root.md) — Cómo se implementan las defensas
- [Domain](../domain/root.md) — Invariantes de negocio que sustentan seguridad

---

**Estado**: S0+S1 STABLE, S2 DRAFT
**Última actualización**: 2026-06-27
**Responsable**: Tech Lead
**Siguiente nodo recomendado**: [domain/root.md](../domain/root.md)
