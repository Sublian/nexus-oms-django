# Nexus OMS — Enterprise Multi-Tenant Operational Commerce Platform

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-6.0%2B-green)](https://www.djangoproject.com/)
[![Architecture](https://img.shields.io/badge/architecture-Clean%20%2B%20DDD-orange)](#arquitectura)
[![Coverage](https://codecov.io/gh/Sublian/nexus-oms-django/branch/main/graph/badge.svg)](https://codecov.io/gh/Sublian/nexus-oms-django)
[![CI](https://github.com/Sublian/nexus-oms-django/actions/workflows/ci.yml/badge.svg)](https://github.com/Sublian/nexus-oms-django/actions/workflows/ci.yml)

Nexus OMS es una plataforma moderna de **Order Management System (OMS)** multi-tenant diseñada para el comercio operacional, facturación electrónica, integraciones y trazabilidad financiera.

A diferencia de los e-commerce convencionales, Nexus se enfoca en:

- **Visibilidad operacional**
- **Aislamiento por tenant**
- **Arquitectura orientada a servicios**
- **Flujos de trabajo asíncronos**
- **Consistencia financiera**
- **Diseño observability-first**

La plataforma está siendo construida como una base SaaS escalable para operaciones de comercio en Latinoamérica y ecosistemas de facturación electrónica.

---

## 🌎 Documentación

📘 La documentación en español y notas técnicas detalladas están disponibles en:

```
/docs
```

Archivos principales:

- `docs/README_ES.md`
- `docs/architecture.md`
- `docs/installation.md`
- `docs/operational_roadmap.md`
- `docs/resume.md`

---

## 🧱 ¿Qué problema resuelve?

Nexus OMS es un **Order Management System multi-tenant** pensado para e-commerce y SaaS B2B, donde cada cliente (tenant) puede gestionar sus órdenes, inventario y operaciones sin mezclar datos con otros tenants. El sistema prioriza la visibilidad operacional, la trazabilidad financiera y la escalabilidad sin reescribir el núcleo del negocio.

---

## 🚀 Características Principales

### Multi-tenancy Estricto

Aislamiento a nivel de organización mediante:

- Propagación de contexto por middleware
- Filtrado de queries por tenant
- Servicios con scope propio
- Analytics aislados por tenant

Cada organización opera de forma independiente sin fuga de datos entre tenants.

### Core de Pedidos (OMS)

Gestión completa del ciclo de vida de las órdenes:

```
pending → paid → shipped → delivered → completed → returned
```

Incluye:

- Flujos de entrega y recogida en tienda
- Logística inversa
- Reconciliación de pagos
- Transiciones operacionales

### Pipeline de Facturación Electrónica (SUNAT Ready)

Arquitectura de facturación desacoplada que soporta:

- Gestión de estados de facturas
- Sincronización asíncrona con reintentos
- Dead letter queues
- Auditabilidad completa
- Abstracción de proveedores

Proveedor actual (mock): **Nubefact** (arquitectura adapter-ready). Nuevas integraciones pueden añadirse sin reescribir el dominio.

### Dashboard Operacional

Panel de observabilidad operacional en tiempo real con:

- KPIs de facturación
- Tasa de aceptación SUNAT
- Latencia de proveedores
- Validación de consistencia contable
- Visibilidad de la cola de sincronización
- Monitoreo de errores terminales
- Analytics de facturas

Diseñado para operadores, no solo administradores.

### Integraciones Externas

Capa de integración orientada a adaptadores preparada para:

- Nubefact
- Shopify
- WooCommerce
- Migo
- Futuros proveedores ERP/pagos

Incluye logging estructurado de requests, tracking de latencia, métricas de errores por proveedor y visibilidad operacional completa.

### Finanzas y Margen Neto

Servicio especializado (`FinanceService`) para calcular rentabilidad real, comisiones y costos, garantizando consistencia financiera en cada operación.

### Arquitectura Orientada a Eventos (EDA)

Procesamiento de tareas pesadas y notificaciones vía **Celery + Redis**, con colas de sincronización, retry tracking y dead letter queues.

---

## 🎨 Estrategia de Frontend: Modern Django

Nexus evita intencionalmente la complejidad innecesaria de los frameworks SPA pesados.

| Tecnología | Rol |
| :--- | :--- |
| **Django Templates** | Renderizado del lado del servidor (SSR) |
| **HTMX** | Actualizaciones parciales reactivas del DOM |
| **TailwindCSS** | Estilos utilitarios y responsivos |
| **Chart.js** | Visualización de analytics |
| **Alpine.js** | Interactividad ligera (dropdowns, tabs) |

Este enfoque reduce la complejidad del frontend, el overhead de hidratación, la fragmentación de herramientas y los costos de mantenimiento, preservando una UX reactiva.

---

## 🏗️ Arquitectura y Filosofía de Diseño

Nexus sigue principios inspirados en:

- **Clean Architecture**
- **Domain Driven Design (DDD)**
- **Service Layer Pattern**
- **Event Driven Thinking**
- **Diseño backend-first**

Prioridades del núcleo:

- Aislar la lógica de negocio
- Reducir el acoplamiento entre módulos
- Mejorar la observabilidad operacional
- Soportar integraciones reemplazables
- Escalar sin reescribir el núcleo

### Capas del Proyecto

| Capa | Responsabilidad |
| :--- | :--- |
| **Domain** | Modelos de negocio, entidades y reglas de dominio |
| **Application** | Casos de uso y orquestación de servicios |
| **Infrastructure** | Integraciones externas y tareas asíncronas |
| **Interface (API/Web)** | Endpoints REST (DRF) y vistas reactivas (HTMX) |

### Servicios Principales

| Servicio | Responsabilidad |
| :--- | :--- |
| `OrderService` | Flujos y transiciones de órdenes |
| `FinanceService` | Cálculos de margen financiero |
| `DashboardKPIService` | Agregación de KPIs operacionales |
| `DailyInvoiceSeriesService` | Analytics y gráficas de facturas |
| `DateRangeService` | Abstracción de filtros temporales |

### Patrones de Diseño Implementados

- **Strategy Pattern:** Sistema de notificaciones multi-canal
- **Service Layer:** Centralización de lógica de negocio compleja
- **Mocker Pattern:** Aislamiento total en tests unitarios asíncronos

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
| :--- | :--- |
| **Backend** | Python 3.12+, Django 6 |
| **API** | Django REST Framework |
| **Frontend** | HTMX + TailwindCSS + Chart.js |
| **Base de Datos** | PostgreSQL |
| **Task Queue** | Celery + Redis |
| **Infraestructura** | Docker, AWS EC2 (Ubuntu + Nginx) |
| **Testing** | Pytest |
| **CI/CD** | GitHub Actions + Codecov |

---

## 📂 Estructura del Repositorio

```text
src/
├── domain/             # Modelos de negocio y reglas de dominio
├── application/        # Casos de uso y servicios de orquestación
├── infrastructure/     # Integraciones externas y tareas asíncronas
├── interfaces/
│   ├── api/            # Endpoints DRF
│   └── web/            # Vistas y templates Django + HTMX
│
├── tests/              # Suite de tests
├── templates/          # Templates compartidos
├── .github/workflows/  # CI Pipeline (Tests & Coverage)
├── docker-compose.yml  # Stack completo de desarrollo
└── docs/               # ADRs, roadmap y notas de arquitectura
```

---

## 🧪 Estrategia de Testing

El proyecto incluye actualmente **220+ tests automatizados** que cubren:

- Servicios de dominio
- Flujos de trabajo de órdenes
- Servicios de analytics
- Aislamiento multi-tenant
- Dashboard KPIs
- Resolución de URLs
- Reglas de negocio
- Flujos de facturación

Filosofía de testing:

- Servicios determinísticos
- Lógica de negocio aislada
- Seguridad en integración
- Prevención de regresiones

---

## 🐳 Desarrollo Local

El proyecto está diseñado para desarrollo **Docker-first**.

**Levantar el stack:**

```bash
docker compose up --build
```

**Ejecutar migraciones:**

```bash
docker compose exec web python manage.py migrate
```

**Generar datos de prueba:**

```bash
docker compose exec web python manage.py seed_data --orders 50
```

**Correr tests:**

```bash
docker compose exec web pytest
```

Para una guía detallada de instalación, consulta [docs/installation.md](docs/installation.md).

---

## 📈 Estado Actual

### Áreas implementadas

- ✅ Arquitectura multi-tenant
- ✅ Flujos OMS completos
- ✅ Cálculos financieros
- ✅ Dashboard operacional
- ✅ Servicios de analytics
- ✅ Pipeline de facturación electrónica
- ✅ Observabilidad de colas
- ✅ Logging de integraciones
- ✅ Flujos asíncronos
- ✅ Dashboard KPIs
- ✅ Analytics con gráficas

### En desarrollo activo

- 🔄 RBAC / permisos granulares
- 🔄 Adaptadores SUNAT reales
- 🔄 Sincronización de inventario
- 🔄 Analytics avanzados
- 🔄 Flujos contables
- 🔄 Pantallas de auditoría operacional

---

## 🧠 Filosofía

> *"Keep the backend intelligent, the frontend thin, and the operations observable."*

Nexus prioriza:

- **Mantenibilidad** sobre complejidad innecesaria
- **Simplicidad operacional** sobre sobre-ingeniería
- **Trazabilidad** sobre opacidad
- **Escalabilidad** sobre reescrituras
- **Velocidad de iteración** sobre perfeccionismo prematuro

---

## 📄 Licencia

Este proyecto se encuentra actualmente en desarrollo privado activo.