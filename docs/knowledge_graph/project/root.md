# Project Root — Nexus OMS Roadmap

## ¿Qué es?

Nexus OMS es un **Sistema de Gestión de Pedidos Multi-Tenant** para e-commerce B2B. Gestiona el ciclo completo: productos, inventario, pedidos, pagos, devoluciones, reportes financieros.

**Alcance actual**:
- ✅ Modelos de dominio (Order, Invoice, Stock, ExchangeRate, etc.)
- ✅ API REST (JWT) + Web Dashboard (sessions + HTMX)
- ✅ Aislación multi-tenant (TenantManager + thread-local)
- ✅ Order FSM + Invoice FSM (paralelo con SUNAT)
- ✅ Celery Beat + Redis para async tasks
- ✅ PostgreSQL con psycopg3

## ¿Por qué existe?

Reemplazar soluciones OMS legacy en Fiberlux (ASP.NET monolítico). Nexus es modular, escalable, con arquitectura limpia (Domain-Driven Design + Clean Architecture).

## Fases Ejecutadas

### S0 — Foundation (Completada)
- Modelos base + migrations
- Multi-tenancy layer
- Authentication (JWT + sessions)

### S1 — Tenant Isolation Hardening (Completada, 337 tests ✅)
- **S1.0**: Audit scope (identificar 4 fugas críticas)
- **S1.1**: Option A defense (Mixin inspection)
- **S1.2**: Option B defense (Global bypass inventory)
- **S1.3**: Option C defense (Centralized enforcement + ViewSet bypass sealing)

**Resultado**: Todas las 4 fugas de tenant selladas. Test suite ejecutada sin regresión.

## Fase Actual

### S2 — Knowledge Graph Foundation (EN PROGRESO)
- Desmantelar snapshot estático → grafo navegable
- Crear 5 nodos core (project, architecture, security, domain, infrastructure)
- Registrar ADRs que justifiquen arquitectura

**Línea de tiempo**: S2.0 inicia 2026-06-27

### S2.X — RLS Hardening (Próximo)
- PostgreSQL Row-Level Security en órdenes críticas
- Audit log para compliance
- Rate limiting + DDoS mitigation

## Stack Técnico

| Componente | Tecnología | Versión |
|-----------|-----------|---------|
| Framework | Django | 6.0.3 |
| API | Django REST Framework | 3.17.1 |
| Auth | djangorestframework-simplejwt | 5.4.0 |
| FSM | django-fsm | 3.0.1 |
| Frontend | HTMX + Tailwind CDN | 1.27.0 |
| Tasks | Celery + Redis | 5.6.3 |
| DB | PostgreSQL via psycopg3 | 3.3.3 |
| Tests | pytest + pytest-django + pytest-cov | 9.0.2 |

## Métricas Clave

- **Tests**: 337 en S1, target 90% coverage
- **Tenants**: Soporta N orgs con aislación garantizada
- **Órdenes/día**: Escalable a 10k+ via Celery
- **Uptime**: Target 99.5% (SLA)

## Siguientes Decisiones

1. ¿Guardar en-grafo decisiones de S2.X (RLS)?
2. ¿Escalar Celery a workers distribuidos o mantener monolítico?
3. ¿Frontend moderno (React) o mantener HTMX?

---

**Estado**: ACTIVE
**Última actualización**: 2026-06-27
**Responsable**: Tech Lead
**Siguiente nodo recomendado**: [architecture/root.md](../architecture/root.md)
