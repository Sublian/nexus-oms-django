# 🧠 Decisiones Arquitectónicas y de Diseño - Nexus OMS

Este documento registra las justificaciones técnicas, evolución de la infraestructura y aprendizajes clave durante el desarrollo de **Nexus OMS**, sirviendo como la "Verdad Única" para el mantenimiento y escalabilidad del sistema.

## 🏛️ Decisiones de Diseño y Evolución

### 1. Arquitectura Multi-tenant (Aislamiento de Datos)
- **Decisión:** Implementar aislamiento mediante `organization_id` a nivel de aplicación (Shared Database).
- **Justificación:** Se priorizó un despliegue ágil y costos contenidos. El aislamiento se garantiza mediante **Custom Managers** de Django que filtran automáticamente por el contexto del Tenant actual, evitando fugas de datos entre organizaciones.

### 2. UI Modular y Patrón de Panel (Sidebar + Navbar)
- **Decisión:** Implementar un layout de tres capas (Navbar superior fijo, Sidebar lateral de navegación y Área de contenido dinámico).
- **Justificación:** Para transformar la aplicación de una "herramienta de una sola página" a un **ERP Profesional**. La separación del Navbar (Gestión de Sesión) y Sidebar (Navegación de Módulos) permite una expansión orgánica de funcionalidades como Inventario, Stock y Finanzas sin saturar la interfaz.

### 3. Interactividad con HTMX y Contenedores de Modales Globales
- **Decisión:** Uso de un contenedor único `<div id="modals-here"></div>` en el `base.html`.
- **Justificación:** Evita la "inyección incrustada" de fragmentos HTML dentro del flujo de la página. Al definir un objetivo (target) global, los detalles de órdenes y formularios de creación se renderizan como capas superiores (Overlays), manteniendo limpia la estructura del DOM principal.

### 4. Gestión de Estado: Borrado Lógico (Idempotencia Financiera)
- **Decisión:** Sustituir la eliminación física de registros por el estado `CANCELLED` (Borrado Lógico) en el modelo `Order`.
- **Justificación:** En sistemas contables y ERPs, la eliminación de datos rompe la trazabilidad y las secuencias de auditoría. Cambiar el estado permite:
    - Mantener el historial de intentos de venta.
    - Visualizar registros anulados (con estilo *line-through* en UI).
    - Evitar errores de integridad referencial en reportes financieros.

### 5. Adopción de Patrones de Diseño (SOLID)
- **Strategy:** El sistema de reportes es agnóstico al canal (Email, PDF).
- **Service Layer (SRP):** La lógica reside en `services/`, evitando "Fat Models".
- **Open/Closed:** El sistema permite añadir nuevos métodos de pago o estados de orden sin modificar el núcleo del dominio.

---

# 🎓 Lecciones Aprendidas y Mejores Prácticas

## 🔄 Resolución de Dependencias Circulares (ADR 003)
**Aprendizaje:** El crecimiento del ERP generó archivos "God" en `domain/`. La solución fue fracturar la capa de dominio en: `models/` (Persistencia), `services/` (Orquestación) y `tasks/` (Asíncrono). El uso de **Lazy Loading** en métodos específicos asegura que los modelos estén cargados antes que las tareas de Celery.

## ⚡ UX con HTMX: `hx-target` y `closest`
**Aprendizaje:** Al realizar acciones sobre tablas (como anular una fila), el uso de `hx-target="closest tr"` permite actualizar solo el fragmento necesario. Esto reduce la carga del servidor y elimina el "parpadeo" de la página, ofreciendo una experiencia similar a una Single Page Application (SPA) pero manteniendo la simplicidad de Django.

## 🛠️ Gestión de Contexto en Tareas Asíncronas
**Aprendizaje:** Se debe serializar y pasar explícitamente el `organization_id` a las tareas de Celery. Esto garantiza que el worker opere siempre bajo el marco de seguridad del Tenant correcto, manteniendo el aislamiento multi-tenant incluso fuera del ciclo de solicitud HTTP.

---

## 📈 Estado de Calidad del Proyecto
- **Code Coverage:** 86% 🚀 (Superando el umbral de producción).
- **Arquitectura:** Domain-Driven Design (DDD) modular.
- **Estándar de Código:** PEP8, principios SOLID y Clean Code.
- **Estado UI:** Layout 100% responsivo con Sidebar dinámico y soporte para Modales.

---
*Última actualización: 5 de Abril de 2026 - Cierre de fase: Módulo de Órdenes y Estructura Base.*