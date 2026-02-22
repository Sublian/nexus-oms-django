# 🗺️ Nexus Project Roadmap

Este documento detalla los hitos de desarrollo y objetivos técnicos del proyecto.

## Hito 1: Cimientos y Multi-tenancy 🏗️
- [ ] Definición de arquiectura y diagramas
- [ ] Configuración basica del proyecto
- [ ] Configuración de Docker (Postgres, Redis, Celery).
- [ ] **TenantMiddleware** y aislamiento de base de datos.
- [ ] Implementación de `CustomUser` y RBAC (roles).
- [ ] Esquema inicial de Base de Datos para el catálogo y organizaciones.

## Hito 2: Core de Pedidos (OMS) 📦
- [ ] Definición de Entidades de Dominio (Python puro).
- [ ] Implementación de las Entidades de Dominio (Order, Item) en Python puro.
- [ ] Implementación de Repositorios e interfaces.
- [ ] Creación de Repositories para desacoplar el ORM.
- [ ] Máquina de Estados (FSM) para órdenes.
- [ ] Configuración de django-fsm para la Máquina de Estados de los pedidos.

## Hito 3: Reactividad con HTMX y Async (HTMX & Celery) ⚡
- [ ] Dashboard administrativo con **HTMX**.
- [ ] Integración de **HTTPX** para servicios externos.
- [ ] Integración de Celery + Redis: Tareas de background para simular pagos.
- [ ] Uso de HTTPX (Async) para verificar stock en servicios externos o consultar divisas.
- [ ] Workers de **Celery** para procesos pesados.

## Hito 4: El Toque Senior (Observabilidad y API) 🐱‍💻
- [ ] Implementación de Audit Logs: Historial de movimientos de cada pedido.
- [ ] Documentación interactiva con Swagger/Spectacular.
- [ ] Setup de CI/CD (GitHub Actions) para ejecución de tests.
...