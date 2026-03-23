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

## Hito 2: Core de Catálogo e Inventario 📦 (COMPLETADO ✅)

**Objetivo**: Modelar el núcleo de productos e inventario, con lógica de impuestos por organización y base para el OMS.

- [x] Modelos de Producto, Categoría, Bodega y Stock.
- [x] Lógica de impuestos configurable por Organización/Tenant.
- [x] Endpoints de API para Catálogo e Inventario (crud funcional).
- [x] Pruebas de validación de stock vía API (unitarias + integración). El sistema descuenta y repone stock correctamente.
- [x] Validación de que todas las consultas respeten el contexto de tenant.
- [x] Testing Suite (Pytest): Implementación de arquitectura de tests con fixtures para Organization, Warehouse y Supplier.
- [x] Stock Logic Tests: Validación de integridad referencial (Warehouse-Stock) y persistencia.

**Resultado esperado**:  
Cada tenant puede gestionar su propio catálogo e inventario, con impuestos específicos, a través de endpoints REST básicos.

---

## Hito 3: Gestión de Pedidos y Logística Inversa 🧾 (COMPLETADO ✅ — Refactorizado)

**Objetivo**: Implementar el flujo principal de órdenes (Order Management System).

- [x] Modelos de Order, OrderItem y OrderReturn.
- [x] Servicio de dominio para cálculo de totales, descuentos e impuestos.
- [x] Endpoints de creación de pedidos (POST).
- [x] Blindaje de Devoluciones: Validación de techo de devolución, bloqueo de cantidades negativas y ceros.
- [x] Pruebas de integración de flujo completo (Venta -> Retorno -> Reposición de Stock).
- [x] Domain Unit Tests: Cobertura del 91% en OrderService y 96% en modelos de venta.

**Resultado esperado**:  
Es posible crear y consultar pedidos respetando las reglas de negocio principales del OMS.

---

## Hito 4: Reactividad y Procesos Asíncronos - HTMX & Celery ⚡ (EN PROGRESO – ~60%)

**Objetivo**: Mejorar la experiencia de usuario y soportar procesos de larga duración mediante tareas en background.

- [x] Capa de Caché con Redis: Optimización de reportes mensuales para evitar hits innecesarios a Postgres.
- [x] Integración de **Celery + Redis** para tareas de background (simulación de pagos, actualizaciones de estado).
- [x] Workers de **Celery** para procesos pesados (recalcular reportes, sincronizar datos).
- [x] Mocker Pattern: Implementación de mocks para tareas asíncronas en tests unitarios, evitando hit a Redis durante el testing.
- [x] Dashboard administrativo con HTMX y Tailwind (Layout base y configuración de Tenant).
- [ ] Async Testing: Pruebas unitarias para tareas de Celery usando mock para evitar ejecución real de Redis en tests unitarios.
- [ ] Uso de HTTPX (**async**) para verificar stock externo o divisas.
- [ ] Dashboard administrativo con **HTMX**

**Resultado esperado**:  
El sistema puede ejecutar procesos lentos fuera del request/response, y el panel administrativo muestra cambios sin recargar toda la página.

---

## Hito 5: El Toque Senior (Observabilidad, Calidad y API) 🐱‍💻 (EN PROGRESO)

**Objetivo**: Llevar el proyecto a un estándar más cercano a producción: observabilidad, calidad y experiencia de integración.

- [x] Documentación interactiva de la API con **Swagger / drf-spectacular**.
- [x] High-Quality Coverage: Alcanzado el 86% de cobertura total del proyecto.
- [ ] Implementación de **Audit Logs**: historial de movimientos y cambios por pedido/entidad relevante.
- [ ] Setup de **CI/CD (GitHub Actions)**: Para automatizar la ejecución de este nuevo suite de 18+ tests.
- [ ] Hardening de Seguridad (PRÓXIMO PASO): Rate limiting por Org-ID, Circuit Breaker, bloqueo por IP.
- [ ] Mailing System: Notificaciones de reportes y alertas de bodega (Hito inmediato).
- [ ] Métricas básicas de rendimiento y salud (endpoints de health check, tiempos de respuesta, etc.).
- [ ] Hardening de seguridad (rate limiting, permisos finos, validación extra de inputs).

**Resultado esperado**:  
El proyecto se comporta como una base creíble para un servicio SaaS: auditable, observable y con una API bien documentada.

---

## Notas de la versión actual (v0.25 - "Analytics & Resilience")

- BI Avanzado: Consolidación de lógica de reportes con cálculo de crecimiento neto/bruto.

- Protección de Datos: Auto-corrección y blindaje contra inconsistencias en el flujo de retornos.

- Cache Layer: Redis operando como capa de optimización de lectura para analítica.

---

## Notas de la versión actual (v0.30 - "The Modular Leap")

- Arquitectura Limpia: El dominio ya no es un "monolito de archivos", sino un sistema de sub-paquetes.

- Precisión Financiera: Integración de Payment con FinanceService para reportes de rentabilidad real (Net Margin).

- Resiliencia de Tests: Eliminación de falsos positivos mediante el uso correcto de mocker.patch y absoluta resolución de paths.

---
## Cómo leer este Roadmap

- Si eres reviewer de **arquitectura**:
  - Revisa Hito 1 y 2 para entender cimientos y multi-tenancy.
  - Revisa Hito 3 para ver cómo se modela el flujo principal de negocio (Orders).

- Si te interesa la parte **DevOps / calidad**:
  - Enfócate en Hito 4 y 5 (Celery, HTMX, CI/CD, observabilidad).

- Este roadmap evoluciona junto con el proyecto:
  - Cuando un hito esté suficientemente estable, se mapeará a una versión (por ejemplo `v0.1 – Core OMS`, `v0.2 – Multi-tenant + Async`).
