# Architecture Decision Records & System Design: Nexus OMS

Este documento detalla las decisiones arquitectónicas, patrones de diseño y la estructura técnica de **Nexus**, una plataforma SaaS de E-commerce Multi-tenant.

---

## 1. Visión General del Proyecto
**Nexus** no es solo un carrito de compras; es un **Order Management System (OMS)** diseñado para alta disponibilidad y escalabilidad. Su propósito es permitir que múltiples empresas (Tenants) gestionen catálogos y pedidos complejos desde una infraestructura única, manteniendo un aislamiento total de datos y lógica de negocio extensible.

### Diagrama de Flujo: HTMX + Django + Celery

```mermaid
    participant U as Usuario (HTMX)
    participant D as Django View
    participant C as Celery Worker
    participant R as Redis (State)

    U->>D: POST /orders/1/pay (hx-post)
    D->>C: Delay Task: ProcessPaymentTask
    D-->>U: Return HTML Snippet (Status: Processing...)
    
    loop Polling with hx-get
        U->>D: GET /orders/1/status
        D->>R: Check Task Status
        R-->>D: Task Completed
        D-->>U: Return HTML Snippet (Status: Paid ✅)
    end
```
---

## 2. Estructura de Capas (Clean Architecture)
Para evitar el acoplamiento excesivo al framework Django, el proyecto se divide en cuatro capas concéntricas:

### 2.1  Diagrama de la Arquitectura de Capas (Clean Architecture)

Este diagrama muestra cómo las dependencias siempre apuntan hacia adentro, hacia el Dominio.

```mermaid
graph TD
    subgraph "External World"
        Web[Web Browser / Mobile App]
    end

    subgraph "Interface / API Layer"
        DRF[Django Rest Framework]
        Serializers[Serializers]
    end

    subgraph "Application Layer (Use Cases)"
        UC[PlaceOrderUseCase]
        UC2[RefundOrderUseCase]
    end

    subgraph "Domain Layer (Core)"
        Entities[Entities: Order, Product]
        Rules[Business Rules]
    end

    subgraph "Infrastructure Layer"
        ORM[Django ORM / PostgreSQL]
        Gateways[Payment Gateways / Stripe]
        Celery[Celery Workers]
    end

    Web --> DRF
    DRF --> UC
    UC --> Entities
    UC --> ORM
    UC --> Gateways
    UC --> Celery
```

* **Dominio (Domain):** El corazón del sistema. Contiene las **Entidades** (clases Python puras como `Order`, `Product`) y **Servicios de Dominio**. No importa qué base de datos o API usemos; las reglas de oro del negocio viven aquí.
* **Aplicación (Application):** Define los **Casos de Uso** (ej. `PlaceOrderWorkflow`). Orquestan la interacción entre el dominio y los servicios externos.
* **Infraestructura (Infrastructure):** Implementaciones concretas. Aquí reside el **Django ORM**, los clientes de Stripe/PayPal, y el sistema de archivos.
* **Interfaz (Interface/API):** El punto de contacto externo. Incluye los **ViewSets** de Django Rest Framework, Serializers y documentación Swagger.

---

## 3. Pilares "Invisibles" de Ingeniería

### A. Multi-tenancy (Estrategia de Aislamiento)
Se ha implementado una estrategia de **Shared Database con Discriminador**.
* **Mecanismo:** Un Middleware identifica al `tenant` mediante el subdominio o el header `X-Tenant-ID`.
* **Seguridad:** Se utiliza un `Global Tenant Manager` en los modelos de Django que añade automáticamente un filtro `WHERE tenant_id = X` a todas las consultas, previniendo la fuga de datos (Data Leakage) entre clientes.

### Diagrama de Aislamiento Multi-tenant (Middleware)
Este es crucial para explicar el pilar "invisible". Muestra cómo el sistema decide qué datos mostrar dependiendo de quién pregunta.

```mermaid
graph LR
    UserA[Client Store A] -->|Subdomain: store-a.nexus.com| MW[Tenant Middleware]
    UserB[Client Store B] -->|Subdomain: store-b.nexus.com| MW
    
    subgraph "Request Lifecycle"
        MW --> Context[Set TenantContext]
        Context --> Manager[Global Tenant Manager]
    end
    
    subgraph "Database (Shared)"
        Manager --> QueryA[(Query: WHERE tenant_id = 'A')]
        Manager --> QueryB[(Query: WHERE tenant_id = 'B')]
    end
```

### B. Arquitectura Orientada a Eventos (EDA)

El sistema utiliza un bus de mensajes (RabbitMQ/Redis) para desacoplar procesos pesados.
* **Flujo:** Al completar un pedido, el dominio emite un evento `OrderConfirmed`.
* **Consumidores:** Workers de **Celery** capturan este evento para:
    1.  Generar la factura legal (PDF).
    2.  Sincronizar el inventario con almacenes externos.
    3.  Enviar notificaciones push/email.

### Diagrama de Flujo del Proceso de Compra (Asíncrono)

Este explica el pilar "invisible" de la Arquitectura Orientada a Eventos (EDA).

```mermaid
sequenceDiagram
    participant C as Client
    participant API as Django API
    participant DB as PostgreSQL
    participant B as Message Broker (RabbitMQ)
    participant W as Celery Workers

    C->>API: POST /orders/ (Place Order)
    API->>API: Validate Domain Logic
    API->>DB: Save Order (Status: PENDING)
    API->>B: Emit Event: ORDER_CREATED
    API-->>C: 202 Accepted (Order ID)
    
    Note over B,W: Async Processing
    B->>W: Consume ORDER_CREATED
    W->>W: Process Payment (Stripe)
    W->>DB: Update Status: PAID
    W->>W: Send Confirmation Email
```

---

## 4. Patrones de Diseño Clave

| Patrón | Propósito en Nexus |
| :--- | :--- |
| **Repository Pattern** | Abstrae el ORM de Django. Los Casos de Uso piden datos a una interfaz, no a `Model.objects.all()`. |
| **Strategy Pattern** | Utilizado en el **Motor de Promociones** para intercambiar algoritmos de descuento (2x1, % fijo, envío gratis) en tiempo de ejecución. |
| **State Pattern (FSM)** | Controla el flujo de los pedidos. Evita estados inválidos (ej. pasar de `CANCELLED` a `SHIPPED`). |
| **Dependency Injection** | Los repositorios se inyectan en los Casos de Uso, permitiendo realizar Unit Testing real sin tocar la base de datos. |


### Diagrama de la Máquina de Estados (Order Life Cycle)

Este demuestra el uso de FSM (Finite State Machine) en el módulo de Pedidos.

```mermaid
stateDiagram-v2
    [*] --> PENDING
    PENDING --> PAID: Payment Success
    PENDING --> CANCELLED: Payment Failed / Timeout
    PAID --> SHIPPED: Logistics Dispatch
    SHIPPED --> DELIVERED: Confirm Receipt
    PAID --> REFUNDED: Admin Action
    DELIVERED --> [*]
    CANCELLED --> [*]
    REFUNDED --> [*]
```
---

## 5. Architecture Decision Records (ADRs)

### ADR 001: Adopción de Monolito Modular vs Microservicios
* **Contexto:** El proyecto requiere alta cohesión pero debe ser fácil de desplegar.
* **Decisión:** Usar un Monolito Modular donde cada app de Django es un "Bounded Context" de DDD.
* **Consecuencia:** Facilidad de desarrollo inicial con una ruta clara para extraer módulos a microservicios si la carga lo requiere.

### ADR 002: Lógica de Negocio fuera de los Modelos
* **Contexto:** Django promueve "Fat Models", lo que dificulta las pruebas y el mantenimiento.
* **Decisión:** Los modelos de Django son solo esquemas de persistencia. La lógica reside en `domain/services.py`.
* **Consecuencia:** Código más verboso pero extremadamente fácil de testear con `pytest`.

### ADR 003: PostgreSQL para Datos Relacionales + JSONB
* **Contexto:** Los productos tienen atributos dinámicos (talla, color, voltaje).
* **Decisión:** Usar PostgreSQL con campos **JSONB** para atributos variables, manteniendo el rigor relacional para transacciones financieras.

---

## 6. Diagrama de Flujo de Datos (Pedido)

1.  **Request:** Cliente envía POST a `/api/orders/`.
2.  **API Layer:** El Serializer valida el formato.
3.  **Application Layer:** El Caso de Uso `CreateOrder` pide al `InventoryRepository` validar stock.
4.  **Domain Layer:** La entidad `Order` calcula totales y aplica impuestos.
5.  **Infrastructure Layer:** El `DjangoOrderRepository` guarda en Postgres.
6.  **Events:** Se dispara tarea asíncrona en Celery para el pago.


---

## 7. Modelado de Datos.

### 7.1. Diagrama de Relación de Entidades (ERD) - Enfoque OMS
Este diagrama muestra cómo se estructuran los datos para soportar el módulo complejo (OMS) y el Multi-tenancy.

```mermaid
erDiagram
    TENANT ||--o{ PRODUCT : owns
    TENANT ||--o{ ORDER : manages
    PRODUCT ||--o{ ORDER_ITEM : included_in
    ORDER ||--|{ ORDER_ITEM : contains
    ORDER ||--o{ ORDER_STATUS_HISTORY : tracks
    CUSTOMER ||--o{ ORDER : places

    ORDER {
        uuid id
        string status
        decimal total_amount
        datetime created_at
    }
    PRODUCT {
        uuid id
        string sku
        jsonb attributes
        decimal price
    }
    ORDER_STATUS_HISTORY {
        string from_status
        string to_status
        string comment
        datetime changed_at
    }
```

---

## 8. Despliegue y DevOps.

### Diagrama de Infraestructura (Docker Compose)
Este diagrama ayuda a visualizar cómo interactúan todos los servicios del stack tecnológico. Es el mapa de tu docker-compose.yml.

```mermaid
graph TD
    subgraph "Public Network"
        NGINX[Nginx Reverse Proxy]
    end

    subgraph "Application Tier"
        Django[Django API / Gunicorn]
        Worker[Celery Worker: Emails/Payments]
        Beat[Celery Beat: Cron Jobs]
    end

    subgraph "Data Tier"
        DB[(PostgreSQL)]
        Redis[(Redis: Cache/Broker)]
    end

    NGINX --> Django
    Django --> DB
    Django --> Redis
    Worker --> Redis
    Worker --> DB
    Beat --> Redis
```