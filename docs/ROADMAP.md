# 🗺️ Nexus Project Roadmap

Este documento detalla los hitos de desarrollo y objetivos técnicos del proyecto.

## Hito 1: Cimientos y Multi-tenancy 🏗️ (COMPLETADO)
- [X] Definición de arquiectura y diagramas
- [X] Configuración basica del proyecto
- [X] Configuración de Docker (Postgres, Redis, Celery).
- [X] Middleware de aislamiento de datos.
- [x] Modelo de Organización (Tenants).
- [X] Script de carga de datos (Seeder).

## Hito 2: Core de Pedidos (OMS) 📦 (EN PROGRESO - 80%)
- [x] Modelos de Producto, Categoría, Bodega y Stock.
- [x] Lógica de impuestos por Organización.
- [ ] PENDIENTE: Endpoints de API para Catálogo e Inventario (Lectura/Escritura).
- [ ] PENDIENTE: Pruebas de validación de stock vía API.

## Hito 3: Gestión de Pedidos (Orders)
- [x] Modelos de Order y OrderItem.
- [x] Servicio de Dominio para cálculo de totales e impuestos.
- [ ] Endpoints de creación de pedidos (POST).
- [ ] Validación de reglas de negocio (No mezclar productos de distintas tiendas).

## Hito 4: Reactividad con HTMX y Async (HTMX & Celery) ⚡
- [ ] Dashboard administrativo con **HTMX**.
- [ ] Integración de **HTTPX** para servicios externos.
- [ ] Integración de Celery + Redis: Tareas de background para simular pagos.
- [ ] Uso de HTTPX (Async) para verificar stock en servicios externos o consultar divisas.
- [ ] Workers de **Celery** para procesos pesados.

## Hito 5: El Toque Senior (Observabilidad y API) 🐱‍💻
- [ ] Implementación de Audit Logs: Historial de movimientos de cada pedido.
- [ ] Documentación interactiva con Swagger/Spectacular.
- [ ] Setup de CI/CD (GitHub Actions) para ejecución de tests.
...