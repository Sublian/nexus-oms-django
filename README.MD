# Nexus OMS: Enterprise Multi-Tenant E-commerce Platform

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-5.0%2B-green)](https://www.djangoproject.com/)
[![Architecture](https://img.shields.io/badge/architecture-Clean%20%2B%20DDD-orange)](#architecture)

Nexus es una plataforma de **Order Management System (OMS)** de alto rendimiento diseñada bajo un modelo **SaaS Multi-tenant**. A diferencia de los e-commerce convencionales, Nexus separa estrictamente la lógica de negocio de la infraestructura, permitiendo gestionar múltiples tiendas independientes con reglas de negocio complejas y flujos de trabajo asíncronos.



## 🚀 Características Principales (High-Level)

- **Multi-tenancy Riguroso:** Aislamiento de datos por esquema/ID mediante Middleware personalizado.
- **Core de Pedidos (OMS):** Motor de estados complejo (FSM) para la gestión del ciclo de vida de las órdenes.
- **Motor de Promociones:** Basado en el patrón *Strategy* para aplicar descuentos dinámicos.
- **Arquitectura Orientada a Eventos (EDA):** Procesamiento de pagos y notificaciones vía Celery + RabbitMQ.
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
| **Task Queue** | Celery + RabbitMQ / Redis |
| **Testing** | Pytest (Unit, Integration, E2E) |
| **DevOps** | Docker, Docker Compose, GitHub Actions |

---

## 📂 Estructura del Repositorio

```text
src/
├── apps/
│   ├── core/           # Middleware multi-tenant y utilidades globales
│   ├── tenants/        # Gestión de organizaciones y suscripciones
│   └── orders/         # Módulo Complejo (OMS)
│       ├── domain/     # Entidades y lógica de negocio pura
│       ├── application/# Casos de Uso (PlaceOrder, CancelOrder, etc.)
│       ├── infra/      # Implementación de Repositorios y Modelos Django
│       └── api/        # Endpoints y Serializers
├── tests/              # Suite de pruebas organizada por capas
└── config/             # Configuración de settings de Django
```

