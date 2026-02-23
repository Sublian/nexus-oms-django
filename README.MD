# Nexus OMS: Enterprise Multi-Tenant E-commerce Platform

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-5.0%2B-green)](https://www.djangoproject.com/)
[![Architecture](https://img.shields.io/badge/architecture-Clean%20%2B%20DDD-orange)](#architecture)

Nexus es una plataforma de **Order Management System (OMS)** de alto rendimiento diseñada bajo un modelo **SaaS Multi-tenant**. A diferencia de los e-commerce convencionales, Nexus separa estrictamente la lógica de negocio de la infraestructura, permitiendo gestionar múltiples tiendas independientes con reglas de negocio complejas y flujos de trabajo asíncronos.

---

## 🧱 ¿Qué problema resuelve?

Nexus OMS es un **Order Management System multi-tenant** pensado para e‑commerce y SaaS B2B, donde cada cliente (tenant) puede gestionar sus órdenes, inventario y operaciones sin mezclar datos con otros tenants.

## 🚀 Características Principales (High-Level)

- **Multi-tenancy Riguroso:** Aislamiento de datos por esquema/ID mediante Middleware personalizado.
- **Core de Pedidos (OMS):** Motor de estados complejo (FSM) para la gestión del ciclo de vida de las órdenes.
- **Motor de Promociones:** Basado en el patrón *Strategy* para aplicar descuentos dinámicos.
- **Arquitectura Orientada a Eventos (EDA):** Procesamiento de pagos y notificaciones vía Celery.
- **Observabilidad:** Logs estructurados y trazabilidad completa de cambios de estado (Audit Logs).

---

## 🏗️ Arquitectura y Patrones

El proyecto implementa **Clean Architecture** para garantizar que el sistema sea fácil de mantener y testear.

### Capas del Proyecto
1. **Domain:** Entidades puras y reglas de oro del negocio. Cero dependencias externas.
2. **Application:** Casos de uso (Orquestación). Aquí reside el "qué hace" el sistema.
3. **Infrastructure:** Adaptadores de base de datos (Django ORM), clientes de API y servicios externos.
4. **Interface (API):** Controladores de Django Rest Framework y Serializers.

### Patrones de Diseño Implementados
* **Repository Pattern:** Desacoplamiento total del ORM.
* **Service Layer:** Lógica de orquestación de procesos complejos.
* **Domain Events:** Comunicación desacoplada entre módulos.
* **Dependency Injection (DI):** Inyección de dependencias para facilitar Unit Testing.

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
| :--- | :--- |
| **Backend** | Python 3.12+, Django 5.x, DRF |
| **Base de Datos** | PostgreSQL (JSONB support) |
| **Task Queue** | Celery + Redis |
| **Testing** | Pytest (Unit, Integration, E2E) |
| **DevOps** | Docker, Docker Compose, GitHub Actions |

---

## 📂 Estructura del Repositorio

```text
/nexus_project
│
├── src/
│   ├── domain/              # Reglas de negocio (Python Puro)
│   ├── application/         # Casos de uso (PlaceOrder, etc)
│   ├── infrastructure/      # Adaptadores (Postgres, HTTPX Clients, Celery Tasks)
│   └── interfaces/          # Web (HTMX Views), API (DRF), Templates
│
├── templates/               # Fragmentos de HTML para HTMX
├── static/                  # Tailwind CSS
├── docker-compose.yml       # Django, Postgres, Redis, Celery Worker, Mailhog
└── Makefile                 # Comandos: make test, make build, make logs
```

## 📌 Estado actual del proyecto

Este repositorio está en construcción activa. A día de hoy:

- [x] Definido el **modelo de capas** (Domain, Application, Infrastructure, Interfaces).
- [x] Documentada la **estrategia multi-tenant** a nivel de middleware y repositorios.
- [ ] Implementación completa de agregados de dominio (Order, Product, Inventory).
- [ ] API REST para órdenes, productos y clientes.
- [ ] Integración con Celery para procesos asincrónicos (events/handlers).
- [ ] Batería de tests (unitarios, integración, contratos) alineada con DDD.


## 📖 Documentación Detallada

Para comprender a fondo las decisiones técnicas y el plan de ejecución, revisa los documentos en la carpeta [`docs/`](./docs/):

* [**Architecture & Design**](./docs/ARCHITECTURE.md): Diagramas de capas, flujo asíncrono y máquina de estados.
* [**Modern Stack Strategy**](./docs/STACK.md): Justificación del uso de HTMX, HTTPX y arquitectura basada en eventos.
* [**Roadmap & Milestones**](./docs/ROADMAP.md): Seguimiento detallado del progreso y objetivos técnicos.
