# NODE_TYPES — Authorized Types

**Objetivo**: 7 tipos de nodo. Claro. Finito. No extensible (evita proliferación).

---

## 1. **Root**
**Definición**: Punto de entrada a un dominio. Mapea regiones + punto cardinal.

**Cuándo usarlo**:
- Entrada a una región (project/root, domain/root, security/root)
- Visión macro + roadmap

**Ejemplos**:
- `project/root.md` — Roadmap macro
- `architecture/root.md` — Stack + interfaces
- `domain/root.md` — Reglas de negocio

**Contenido típico**:
- Resumen del dominio
- Subnodos principales (con links)
- Roadmap si aplica

---

## 2. **Entity**
**Definición**: Modelo de dominio o abstracción clave del sistema.

**Cuándo usarlo**:
- Modelos: Order, Invoice, Stock, User
- Conceptos persistentes

**Ejemplos**:
- `domain/order-fsm.md` — Order entity + transitions
- `domain/stock-movement.md` — Stock audit trail
- `domain/exchange-rate.md` — Finance entity

**Contenido típico**:
- Estructura (campos clave)
- Invariantes
- Transiciones (si FSM)

---

## 3. **Domain**
**Definición**: Regla, patrón o proceso de negocio (no es entidad).

**Cuándo usarlo**:
- Procesos: "Invoice Pipeline", "Tenant Isolation Mechanism"
- Patrones: "Idempotency Guards", "Thread-Local Context"
- Reglas sin persistencia propia

**Ejemplos**:
- `domain/invoice-pipeline.md` — 3 fases de facturación
- `infrastructure/tenant-thread-local.md` — Patrón thread-local
- `domain/stock-signals-design.md` — Cómo se ajusta stock

**Contenido típico**:
- Descripción del patrón
- Por qué existe
- Diagrama simple (ASCII ok)

---

## 4. **Security**
**Definición**: Mecanismo de defensa, protección, invariante de seguridad.

**Cuándo usarlo**:
- Guards: `select_for_update()`, invariantes
- Aislación: tenant filters, RBAC
- Riesgos y mitigaciones

**Ejemplos**:
- `security/tenant-bypass-invariant.md` — NUNCA .all_objects
- `security/superuser-org-context.md` — Riesgo superuser
- `domain/invoice-idempotency-guards.md` — Dedup guards

**Contenido típico**:
- Qué se defiende
- Cómo funciona
- Qué pasa si falla

---

## 5. **ADR** (Architecture Decision Record)
**Definición**: Decisión arquitectónica + razón + alternativas rechazadas.

**Cuándo usarlo**:
- Decisiones significativas (S1 vs S2, JWT vs sessions)
- Compromisos tech
- Impacta roadmap

**Ejemplos**:
- `decisions/ADR-001.md` — Why App Guards BEFORE RLS
- `decisions/ADR-002.md` (futuro) — Why PostgreSQL not NoSQL

**Contenido típico**:
- Context
- Decision
- Reasoning
- Alternatives rejected
- Consequences

---

## 6. **Integration**
**Definición**: Interfaz con sistema externo o dependencia.

**Cuándo usarlo**:
- Clientes API: APIMigo, Nubefact
- Proveedores: JWT, Celery, Redis
- Contratos con terceros

**Ejemplos**:
- `infrastructure/nubefact-client.md` — Invoice provider
- `infrastructure/apimigo-client.md` — Exchange rate API
- `infrastructure/celery-broker.md` — Task queue

**Contenido típico**:
- Contrato (endpoints, métodos)
- Error handling
- Fallback strategy

---

## 7. **Roadmap**
**Definición**: Plan futuro, fase, iniciativa, hito.

**Cuándo usarlo**:
- Phases: S2, S3, etc.
- Features planned
- Milestones

**Ejemplos**:
- `project/root.md` — S0 → S1 → S2 → ...
- `security/root.md` — S2.1 RLS Policy Design (futuro)

**Contenido típico**:
- Fases/steps
- Timeline (si aplica)
- Success criteria
- Blocked by / Depends on

---

## Type Distribution Target (MVP)

```
Root         — 6 (project, architecture, security, domain, infrastructure, decisions)
Entity       — 12 (Order, Invoice, Stock, PurchaseOrder, etc.)
Domain       — 15 (patterns, processes)
Security     — 10 (guards, invariantes, risks)
ADR          — 5-10 (decisiones significativas)
Integration  — 8 (APIMigo, Nubefact, Celery, Redis, etc.)
Roadmap      — 5 (phases, milestones)
─────────────────────────
TOTAL        ≈ 60 nodos (Completable MVP, no masivo)
```

---

## Validation

Cada `.md` en `docs/knowledge_graph/` debe tener:
```yaml
type: [Root|Entity|Domain|Security|ADR|Integration|Roadmap]
```

Si no califica → NO entra al grafo. Edita nodo existente en cambio.

---

**Versión**: 1.0
**Efectiva desde**: 2026-06-27
**Próxima revisión**: Cuando excedamos 50 nodos
