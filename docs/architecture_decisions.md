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

- Decisión: Uso estricto de Singleton, Strategy (en notificaciones) y Factory (en tests).

- Justificacion: 

- Strategy: Permite que el sistema de reportes sea agnóstico al canal de salida (Email, Slack, PDF).
- Singleton: Garantiza la consistencia en el manejo de configuraciones globales del sistema.
- Open/Closed Principle: El sistema debe ser capaz de enviar notificaciones por diversos canales (Email, Slack) sin que el código que genera el reporte tenga que ser modificado.

4. Estrategia de Testing (80% Code Coverage)
- Decisión: Establecer un umbral mínimo de cobertura del 80% usando Pytest y cobertura de integración.

- Justificacion: Se priorizaron los tests de Capa de Negocio (Domain) y Casos de Borde (Edge Cases). Alcanzar el 80% garantiza que cualquier refactorización futura (como una migración de versión de Django u Odoo) sea segura y predecible.

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
# ADR 003: Modularization of the Domain Layer

## Status
Accepted

## Context
As the ERP/CRM system grew, the `domain` folder became a "God Folder" with too many responsibilities in single files, leading to circular imports between services and Celery tasks.

## Decision
We decided to split the `domain` layer into three specialized sub-packages:
1. `models/`: Pure data structures and persistence logic.
2. `services/`: Complex business logic and cross-model orchestrations.
3. `tasks/`: Asynchronous operations (Celery).

We also enforced the use of absolute imports (e.g., `from src.domain.tasks import ...`) to avoid ambiguity during package resolution.

## Consequences
- **Positive**: Better testability, elimination of circular dependencies, and clearer separation of concerns (SOLID).
- **Negative**: Requires more care with import paths and updated mocker paths in existing tests.