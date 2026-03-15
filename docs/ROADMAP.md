# 🗺️ Nexus Project Roadmap

Este documento detalla los hitos de desarrollo y los objetivos técnicos del proyecto.  
Es la **fuente de verdad** sobre qué está hecho y qué falta por implementar.

> Nota: En el README se habla de M1/M2/M3 como niveles de madurez.  
> En esta primera versión, los hitos se organizan como Hito 1, 2, 3, etc.  
> Más adelante se mapearán estos hitos a releases (v0.1, v0.2, v0.3).

---

## Hito 1: Cimientos y Multi-tenancy 🏗️ (COMPLETADO ✅)

**Objetivo**: Tener una base sólida del proyecto con arquitectura definida, entorno listo y soporte multi-tenant a nivel técnico.

- [x] Definición de arquitectura y diagramas (limpia/hexagonal + DDD ligero).
- [x] Configuración básica del proyecto Django (settings, apps, estructura de `src/`).
- [x] Configuración de Docker (Postgres, Redis, Celery).
- [x] Middleware de aislamiento de datos por organización/tenant.
- [x] Modelo de Organización (Tenants).
- [x] Script de carga inicial de datos (Seeder).

**Resultado esperado**:  
El proyecto se puede levantar en local con Docker y ya existe un mecanismo básico para aislar datos por organización.

---

## Hito 2: Core de Catálogo e Inventario 📦 (EN PROGRESO – ~80%)

**Objetivo**: Modelar el núcleo de productos e inventario, con lógica de impuestos por organización y base para el OMS.

- [x] Modelos de Producto, Categoría, Bodega y Stock.
- [x] Lógica de impuestos configurable por Organización/Tenant.
- [ ] Endpoints de API para Catálogo e Inventario (lectura/escritura).
- [ ] Pruebas de validación de stock vía API (unitarias + integración).
- [ ] Validación de que todas las consultas respeten el contexto de tenant.

**Resultado esperado**:  
Cada tenant puede gestionar su propio catálogo e inventario, con impuestos específicos, a través de endpoints REST básicos.

---

## Hito 3: Gestión de Pedidos (Orders) 🧾

**Objetivo**: Implementar el flujo principal de órdenes (Order Management System).

- [x] Modelos de Order y OrderItem.
- [x] Servicio de dominio para cálculo de totales, descuentos e impuestos.
- [x] Endpoints de creación de pedidos (POST).
- [ ] Validación de reglas de negocio clave (p. ej. no mezclar productos de distintas tiendas/bodegas).
- [ ] Endpoints de consulta de pedidos (por estado, por cliente, por rango de fechas).
- [ ] Pruebas de reglas de negocio (dominio) y de API para la creación y consulta de órdenes.

**Resultado esperado**:  
Es posible crear y consultar pedidos respetando las reglas de negocio principales del OMS.

---

## Hito 4: Reactividad y Procesos Asíncronos (HTMX & Celery) ⚡

**Objetivo**: Mejorar la experiencia de usuario y soportar procesos de larga duración mediante tareas en background.

- [ ] Dashboard administrativo con **HTMX** (actualización parcial de vistas).
- [ ] Integración de **HTTPX** para comunicación con servicios externos.
- [ ] Integración de **Celery + Redis** para tareas de background (simulación de pagos, actualizaciones de estado).
- [ ] Uso de HTTPX (async) para verificar stock en servicios externos o consultar divisas.
- [ ] Workers de **Celery** para procesos pesados (recalcular reportes, sincronizar datos).

**Resultado esperado**:  
El sistema puede ejecutar procesos lentos fuera del request/response, y el panel administrativo muestra cambios sin recargar toda la página.

---

## Hito 5: El Toque Senior (Observabilidad, Calidad y API) 🐱‍💻

**Objetivo**: Llevar el proyecto a un estándar más cercano a producción: observabilidad, calidad y experiencia de integración.

- [ ] Implementación de **Audit Logs**: historial de movimientos y cambios por pedido/entidad relevante.
- [ ] Documentación interactiva de la API con **Swagger / drf-spectacular**.
- [ ] Setup de **CI/CD (GitHub Actions)** para ejecutar tests y checks automáticos en cada push/PR.
- [ ] Métricas básicas de rendimiento y salud (endpoints de health check, tiempos de respuesta, etc.).
- [ ] Hardening de seguridad (rate limiting, permisos finos, validación extra de inputs).

**Resultado esperado**:  
El proyecto se comporta como una base creíble para un servicio SaaS: auditable, observable y con una API bien documentada.

---

## Cómo leer este Roadmap

- Si eres reviewer de **arquitectura**:
  - Revisa Hito 1 y 2 para entender cimientos y multi-tenancy.
  - Revisa Hito 3 para ver cómo se modela el flujo principal de negocio (Orders).

- Si te interesa la parte **DevOps / calidad**:
  - Enfócate en Hito 4 y 5 (Celery, HTMX, CI/CD, observabilidad).

- Este roadmap evoluciona junto con el proyecto:
  - Cuando un hito esté suficientemente estable, se mapeará a una versión (por ejemplo `v0.1 – Core OMS`, `v0.2 – Multi-tenant + Async`).
