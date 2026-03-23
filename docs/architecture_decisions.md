# 🧠 Decisiones Arquitectónicas y de Diseño - Nexus OMS

Este documento registra las justificaciones técnicas y aprendizajes clave durante el desarrollo de Nexus OMS, sirviendo como guía para el mantenimiento y evolución del sistema.

## 🏛️ Decisiones de Diseño

1. Arquitectura Multi-tenant (Aislamiento de Datos)
- Decisión: Implementar aislamiento mediante organization_id a nivel de aplicación (Shared Database).

- Justificación: Se priorizó una arquitectura que permita un despliegue ágil y costos de infraestructura contenidos, asegurando el aislamiento mediante managers personalizados de Django que filtran automáticamente por el contexto del Tenant actual.

2. Procesamiento Asíncrono con Celery & Redis
- Decisión: Desacoplar procesos costosos (como la generación de reportes de ventas) del hilo principal de la API.

- Justificación: Evitar tiempos de respuesta altos y timeouts. El uso de Redis como broker garantiza una comunicación rápida entre la aplicación y los workers.

3. Adopción de Patrones de Diseño (SOLID)

- Decisión: Uso estricto de Singleton, Strategy y **Service Layer Pattern**.

- Justificación: 
    - **Strategy**: Permite que el sistema de reportes sea agnóstico al canal (Email, Slack, PDF).
    - **Service Layer (SRP)**: Al extraer la lógica de `models.py` hacia `services/`, evitamos los "Fat Models" y facilitamos el testing de flujos complejos como la creación de órdenes y cálculos financieros.
    - **Open/Closed**: El sistema extiende funcionalidades (como nuevos métodos de pago o canales de notificación) sin modificar el núcleo del dominio.

4. Estrategia de Testing (80% Code Coverage)

- Decisión: Mantener un coverage alto (>80%) con enfoque en integración y lógica de negocio.

- Justificación: Alcanzar el **86%** actual garantiza que cualquier refactorización (como la reciente modularización del dominio) sea segura. Se priorizaron los "Happy Paths" financieros y la validación de integridad de stock.

5. Stack Tecnológico Moderno

- Decisión: Uso de Docker, PostgreSQL 17 y Python 3.12.

- Justificacion: Para garantizar la paridad entre los entornos de desarrollo, staging y producción, minimizando los errores de "funciona en mi máquina".

# 🎓 Lecciones Aprendidas y Mejores Prácticas

## 🚀 Por qué Pytest-Django sobre el Runner Estándar

Durante el desarrollo, se optó por pytest-django por encima del comando manage.py test tradicional.

Aprendizaje: Pytest ofrece una sintaxis mucho más limpia y potente gracias a los Fixtures. Esto facilitó la creación de entornos multi-tenant complejos (Organizations, Products, Orders) que pueden reutilizarse en múltiples tests, reduciendo el código repetitivo y mejorando la velocidad de ejecución.

## 🔄 La Importancia de la Idempotencia en las Pruebas

Uno de los retos más grandes fue asegurar que los tests fueran idempotentes (que produzcan el mismo resultado sin importar cuántas veces se ejecuten o el orden de estos).

Aprendizaje: El uso de pruebas automatizadas nos obligó a garantizar que cada ejecución limpie su estado. Sin pruebas, es fácil ignorar efectos secundarios en la base de datos o en el estado de Celery. La idempotencia en los tests es el primer paso para lograr sistemas distribuidos fiables donde las tareas fallidas pueden reintentarse sin corromper los datos.

## 🛠️ Gestión de Contexto en Tareas Asíncronas

Un error común en arquitecturas multi-tenant es perder el contexto del usuario al pasar a un proceso de Celery.

Aprendizaje: Se aprendió a serializar y pasar explícitamente el organization_id a las tareas, asegurando que el worker de Celery opere siempre bajo el marco de seguridad del Tenant correcto, evitando fugas de información entre organizaciones.

## 📈 Estado de Calidad del Proyecto

Code Coverage: 80% (Umbral mínimo de producción).

Calidad de Código: Adhesión estricta a principios SOLID y diseño orientado al dominio (DDD).


---

## 🔄 Resolución de Dependencias Circulares y Modularización (ADR 003)

**Contexto:** El crecimiento del ERP generó archivos "God" en `domain/`, causando errores de importación circular entre la lógica de negocio y las tareas de Celery.

**Decisión:**
- Se fracturó la capa de dominio en tres sub-paquetes: `models/` (Persistencia), `services/` (Orquestación/Lógica) y `tasks/` (Asíncrono).
- Se implementaron **Absolute Imports** y **Lazy Loading** dentro de los métodos de servicio para asegurar que los modelos estén cargados antes que las tareas.

**Aprendizaje:** En Python/Django, la estructura de carpetas dicta la salud de los imports. Separar las tareas asíncronas de los servicios permite testear la lógica de negocio mockeando Celery de forma limpia, sin cargar todo el stack de infraestructura.

## 📈 Estado de Calidad del Proyecto
- **Code Coverage:** 86% 🚀
- **Arquitectura:** Domain-Driven Design (DDD) modular.
- **Estándar de Código:** PEP8 y principios SOLID.