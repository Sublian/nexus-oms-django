# Nexus OMS: Enterprise Multi-Tenant E-commerce Platform

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-5.0%2B-green)](https://www.djangoproject.com/)
[![Architecture](https://img.shields.io/badge/architecture-Clean%20%2B%20DDD-orange)](#architecture)
[![Coverage](https://codecov.io/gh/Sublian/nexus-oms-django/branch/main/graph/badge.svg)](https://codecov.io/gh/Sublian/nexus-oms-django)
[![CI](https://github.com/Sublian/nexus-oms-django/actions/workflows/ci.yml/badge.svg)](https://github.com/Sublian/nexus-oms-django/actions/workflows/ci.yml)

Nexus es una plataforma de **Order Management System (OMS)** de alto rendimiento diseñada bajo un modelo **SaaS Multi-tenant**. A diferencia de los e-commerce convencionales, Nexus separa estrictamente la lógica de negocio de la infraestructura, permitiendo gestionar múltiples tiendas independientes con reglas de negocio complejas y flujos de trabajo asíncronos.

---

## 🧱 ¿Qué problema resuelve?

Nexus OMS es un **Order Management System multi-tenant** pensado para e‑commerce y SaaS B2B, donde cada cliente (tenant) puede gestionar sus órdenes, inventario y operaciones sin mezclar datos con otros tenants.

## 🚀 Características Principales (High-Level)

- **Multi-tenancy Riguroso:** Aislamiento de datos por ID mediante Middleware personalizado y filtrado automático en el ORM.
- **Core de Pedidos (OMS):** Motor de gestión del ciclo de vida de las órdenes y logística inversa protegida.
- **Finanzas y Margen Neto:** Servicio especializado (`FinanceService`) para calcular rentabilidad real, comisiones y costos.
- **Arquitectura Orientada a Eventos (EDA):** Procesamiento de tareas pesadas y notificaciones vía Celery + Redis.
- **CI/CD & Cloud:** Pipeline automatizado con GitHub Actions y despliegue preparado para AWS EC2.

---

## 🎨 Estrategia de Frontend: "The New Django Way"

Nexus rechaza la complejidad innecesaria de los frameworks de JS pesados. En su lugar, utiliza un stack moderno y ligero:

* **HTMX:** Para realizar peticiones AJAX directamente desde HTML, permitiendo actualizaciones parciales del DOM y una sensación de SPA.
* **Tailwind CSS:** Para un diseño utilitario, rápido y totalmente responsivo.
* **Alpine.js (Opcional):** Para lógica de cliente mínima (dropdowns, tabs) sin salir del ecosistema HTML.
* **Django Templates:** Renderizado del lado del servidor (SSR) para máxima velocidad inicial y SEO.

---

## 🏗️ Arquitectura y Patrones

El proyecto implementa **Clean Architecture** y **DDD** para garantizar mantenibilidad.

### Capas del Proyecto
1. **Domain:** Entidades puras, modelos de persistencia y lógica financiera.
2. **Application (Services):** Orquestación de casos de uso (OrderService, FinanceService).
3. **Infrastructure:** Tareas de Celery, adaptadores de DB y configuración de AWS.
4. **Interface (Web/API):** * **API:** Endpoints REST para integraciones externas.
    * **Web:** Vistas reactivas potenciadas por **HTMX** para el operador humano.

### Patrones de Diseño Implementados
* **Strategy Pattern:** En el sistema de notificaciones multi-canal.
* **Service Layer:** Centralización de lógica de negocio compleja.
* **Mocker Pattern:** Para el aislamiento total de tests unitarios asíncronos.

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
| :--- | :--- |
| **Backend** | Python 3.12+, Django 5.x |
| **Base de Datos** | PostgreSQL 17 |
| **Task Queue** | Celery + Redis |
| **Cloud & Infra** | AWS EC2 (Ubuntu + Nginx), Docker |
| **CI/CD** | GitHub Actions + Codecov |

---

## 📂 Estructura del Repositorio

```text
/src
│
├── domain/            # Modelos, Servicios de Dominio y Lógica Financiera
├── application/       # (En transición) Casos de uso
├── infrastructure/    # Tareas de Celery y configuraciones externas
├── interfaces/        # API (DRF) y Vistas Web (HTMX)
│
├── .github/workflows/ # CI Pipeline (Tests & Coverage)
├── docker-compose.yml # Stack completo de desarrollo
└── docs/              # Roadmap, Arquitectura y Decisiones (ADRs)

## 📦 Instalación Rápida

Para una guía detallada de instalación con Docker y VS Code, consulta [installation.md](installation.md).
