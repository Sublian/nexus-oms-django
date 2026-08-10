# Nexus OMS — Plataforma de Comercio Operacional Multi-Tenant

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-6.0%2B-green)](https://www.djangoproject.com/)
[![Architecture](https://img.shields.io/badge/architecture-Clean%20%2B%20DDD-orange)](#arquitectura)
[![Coverage](https://codecov.io/gh/Sublian/nexus-oms-django/branch/main/graph/badge.svg)](https://codecov.io/gh/Sublian/nexus-oms-django)
[![CI](https://github.com/Sublian/nexus-oms-django/actions/workflows/ci.yml/badge.svg)](https://github.com/Sublian/nexus-oms-django/actions/workflows/ci.yml)

> 🌐 English documentation at the root [`README.md`](../README.md)

---

## ¿Qué es Nexus OMS?

Nexus es un **Order Management System (OMS) multi-tenant** pensado para operaciones de comercio B2B y SaaS en Latinoamérica. No es un e-commerce convencional — es una plataforma operacional donde cada cliente (tenant) gestiona sus órdenes, facturación electrónica y finanzas de forma completamente aislada.

El punto de partida del diseño fue una pregunta concreta: ¿cómo construir un sistema que escale sin reescribir el núcleo cada vez que el negocio cambia? La respuesta fue separar estrictamente la lógica de negocio de la infraestructura, y hacer que las operaciones sean observables desde el primer día.

---

## ¿Por qué estas decisiones técnicas?

### Multi-tenancy por middleware, no por base de datos separada

En lugar de crear una base de datos por tenant (costoso y difícil de mantener), Nexus propaga el contexto del tenant en cada request mediante middleware. El ORM filtra automáticamente por organización en cada query. Esto significa que añadir un nuevo cliente no requiere cambios de infraestructura.

### Clean Architecture + DDD: no es solo teoría

La separación en capas (Domain → Application → Infrastructure → Interface) tiene un propósito práctico: cuando cambia un proveedor de facturación (por ejemplo, pasar de Nubefact a otro), solo se reemplaza el adaptador. El dominio no se toca. Esta decisión ya se validó en el diseño del pipeline SUNAT.

### HTMX en lugar de React/Vue

La decisión de evitar frameworks SPA no fue por desconocimiento, sino por pragmatismo. El operador humano que usa el dashboard no necesita una SPA — necesita una interfaz rápida, confiable y con actualizaciones parciales. HTMX entrega exactamente eso con una fracción de la complejidad.

### Celery + Redis para todo lo asíncrono

La sincronización con SUNAT, los reintentos de facturación y las notificaciones son procesos que no pueden bloquear el request del usuario. Celery maneja estas tareas con colas dedicadas, dead letter queues para errores terminales, y visibilidad desde el dashboard operacional.

---

## Flujo principal: de una orden a una factura

```
Orden creada (pending)
    → Pago confirmado (paid)
        → Preparación y envío (shipped)
            → Entrega confirmada (delivered)
                → Ciclo completo (completed)
                    ↘ Devolución (returned) — logística inversa
```

Cada transición tiene validaciones de negocio, registro de eventos y potencial disparo de tareas asíncronas (notificaciones, sincronización con SUNAT, actualización de KPIs).

---

## Arquitectura

### Capas del sistema

| Capa | Qué contiene | Por qué está separada |
| :--- | :--- | :--- |
| **Domain** | Entidades, reglas de negocio, lógica financiera | Es el núcleo — no depende de nada externo |
| **Application** | Servicios de orquestación, casos de uso | Coordina sin conocer detalles de infraestructura |
| **Infrastructure** | Celery, adaptadores externos, configuración AWS | Cambia sin afectar el dominio |
| **Interface** | API REST (DRF) + Vistas web (HTMX) | Capa de entrada — delgada por diseño |

### Servicios principales

| Servicio | Responsabilidad | Contexto de uso |
| :--- | :--- | :--- |
| `OrderService` | Transiciones y reglas del ciclo de vida | Toda operación sobre órdenes pasa por aquí |
| `PaymentService` | Procesamiento de pagos, comisiones y confirmación con la pasarela | Registro de cobros y confirmación asíncrona |
| `FinanceService` | Margen real, comisiones, rentabilidad | Desacoplado del flujo de órdenes |
| `DashboardKPIService` | Agregación de métricas por tenant | Alimenta el dashboard operacional |
| `DailyInvoiceSeriesService` | Series temporales de facturación | Gráficas y analytics |
| `DateRangeService` | Abstracción de filtros temporales | Reutilizable en cualquier servicio |

### Patrones implementados y por qué

**Strategy Pattern en notificaciones:** el sistema puede enviar notificaciones por email, webhook o cualquier canal futuro sin cambiar la lógica de negocio — solo se añade una nueva estrategia.

**Adapter Pattern en integraciones:** Nubefact, Shopify, WooCommerce son adaptadores intercambiables. El dominio solo conoce la interfaz, nunca el proveedor concreto.

**Mocker Pattern en tests:** los tests unitarios de servicios asíncronos no dependen de Redis ni Celery reales — se mockean completamente para garantizar determinismo.

---

## Registro y Sincronización de Pagos

Ciclo de vida completo de cobros con una pasarela mock determinista (Fase A):

- Métodos: **CASH / CARD / TRANSFER / WALLET** con configuración de comisión por tenant (`PaymentFeeConfig`); la comisión se snapshotea al cobrar (`fee_amount`/`fee_rate`)
- **Confirmación asíncrona** para transferencias y Yape/Plin (`pending → approved`): barrido del Celery beat cada 60s + confirmación manual desde dashboard/API
- **Seguro por tenant por diseño**: `PaymentService` gestiona su propio contexto de tenant, de modo que la confirmación funciona desde los workers de Celery sin middleware HTTP
- **Transiciones validadas**: una orden solo pasa a `PAID` si la transición es válida — un pago aprobado jamás revive una orden cancelada
- Endpoints REST: `POST /orders/{id}/pay/`, `GET /orders/{id}/payment/`, `POST /orders/{id}/confirm-payment/`

---

## Pipeline de Facturación Electrónica

Este es uno de los sistemas más complejos del proyecto, diseñado para cumplir con los requisitos de SUNAT (Perú) desde el inicio.

**Decisiones clave:**

- La factura tiene su propio estado independiente del estado de la orden
- La sincronización con SUNAT es siempre asíncrona — nunca bloquea el flujo principal
- Los errores tienen tres categorías: reintentables, terminales (dead letter), y advertencias
- El proveedor actual (Nubefact mock) puede reemplazarse sin tocar nada fuera del adaptador

**Lo que ve el operador en el dashboard:**
- Tasa de aceptación SUNAT en tiempo real
- Profundidad de la cola de sincronización
- Facturas en dead letter (requieren intervención manual)
- Latencia promedio por proveedor

---

## Stack tecnológico

| Componente | Tecnología | Decisión |
| :--- | :--- | :--- |
| **Backend** | Python 3.12+, Django 6 | Madurez, ecosistema, ORM potente |
| **API** | Django REST Framework | Integraciones externas y mobile |
| **Frontend** | HTMX + TailwindCSS + Chart.js | Sin overhead de SPA |
| **Base de datos** | PostgreSQL | ACID, JSON fields, escalabilidad |
| **Cola de tareas** | Celery + Redis | Probado en producción, flexible |
| **Infraestructura** | Docker + AWS EC2 | Reproducibilidad local y cloud |
| **Tests** | Pytest | 390+ tests, cobertura continua |
| **CI/CD** | GitHub Actions + Codecov | Feedback inmediato en cada PR |

---

## Estructura del repositorio

```text
src/
├── domain/             # Núcleo del negocio — sin dependencias externas
├── application/        # Orquestación de casos de uso
├── infrastructure/     # Celery, adaptadores, configuración externa
├── interfaces/
│   ├── api/            # Endpoints REST
│   └── web/            # Vistas HTMX + templates
│
├── tests/              # Suite completa de tests
├── templates/          # Templates compartidos
├── .github/workflows/  # CI automático
├── docker-compose.yml  # Stack de desarrollo completo
└── docs/               # ADRs, roadmap, decisiones de arquitectura
```

---

## Cómo empezar (desarrollo local)

El proyecto está diseñado para correr con Docker desde el primer comando.

```bash
# Levantar el stack completo
docker compose up --build

# Aplicar migraciones
docker compose exec web python manage.py migrate

# Generar datos de prueba realistas
docker compose exec web python manage.py seed_data --orders 50

# Correr la suite de tests
docker compose exec web pytest
```

Para una guía detallada con configuración de VS Code y variables de entorno, ver [`docs/installation.md`](installation.md).

---

## Estado actual del proyecto

### Completado

- ✅ Arquitectura multi-tenant con aislamiento por middleware
- ✅ Flujos OMS completos con transiciones validadas
- ✅ Motor financiero (`FinanceService`)
- ✅ Dashboard operacional con KPIs en tiempo real
- ✅ Servicios de analytics y series temporales
- ✅ Pipeline de facturación electrónica (mock SUNAT)
- ✅ Registro de pagos y sincronización con pasarela
- ✅ Observabilidad de colas y dead letters
- ✅ Logging estructurado de integraciones
- ✅ Flujos asíncronos con Celery

### En desarrollo activo

- 🔄 RBAC — permisos granulares por rol dentro del tenant
- 🔄 Adaptadores SUNAT reales (Nubefact producción)
- 🔄 Sincronización de inventario
- 🔄 Analytics avanzados con comparativas históricas
- 🔄 Flujos contables automatizados
- 🔄 Pantallas de auditoría operacional

---

## Documentación adicional

| Documento | Contenido |
| :--- | :--- |
| [`docs/architecture.md`](architecture.md) | Decisiones de arquitectura (ADRs) |
| [`docs/installation.es.md`](installation.md) | Guía completa de instalación |
| [`docs/operational_roadmap.md`](operational_roadmap.md) | Roadmap y prioridades |
| [`docs/resume.md`](resume.md) | Resumen ejecutivo del proyecto |

---

## Filosofía del proyecto

> *"Keep the backend intelligent, the frontend thin, and the operations observable."*

Nexus no busca ser el sistema más sofisticado tecnológicamente — busca ser el más mantenible y observable. Cada decisión de diseño se evalúa contra tres preguntas: ¿reduce el acoplamiento? ¿mejora la visibilidad operacional? ¿escala sin reescribir?

---

*Este proyecto está actualmente en desarrollo privado activo.*