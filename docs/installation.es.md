# Instalación — Nexus OMS

> Guía de instalación y configuración del entorno de desarrollo local para Nexus OMS — una plataforma multi-tenant de gestión de pedidos con facturación electrónica mock, construida con Django, DRF, HTMX y Celery.

🌐 English version: [`docs/installation.md`](installation.md)

**Método recomendado: Docker Compose.**

---

## ¿Por dónde empezar?

Si es tu primera vez con el proyecto, el camino más rápido es el [Quick Start](#quick-start-5-minutos) con Docker. En menos de 5 minutos tendrás el stack completo corriendo con datos demo realistas que alimentan el dashboard operacional, las colas de facturación y las métricas por tenant.

Si necesitas correr el proyecto sin Docker (por ejemplo, para debugging más directo), la sección [Instalación sin Docker](#instalación-sin-docker) cubre ese flujo completo.

---

## Requisitos

| Herramienta | Versión recomendada | Notas |
| :--- | :--- | :--- |
| Git | Última | — |
| Docker | 24+ | Método recomendado |
| Docker Compose | v2+ | Incluido en Docker Desktop |
| Python | 3.12+ | Solo para instalación sin Docker |
| PostgreSQL | 17 | Solo para instalación sin Docker |
| Redis | 7 | Solo para instalación sin Docker |

---

## Quick Start (5 minutos)

Levanta el stack completo con datos demo realistas en un solo flujo.

```bash
git clone https://github.com/Sublian/nexus-oms-django.git
cd nexus-oms-django
cp .env.example .env
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_data --orders 50
```

### Puntos de acceso

| Servicio | URL |
| :--- | :--- |
| App principal | http://localhost:8000 |
| Django Admin | http://localhost:8000/admin |
| Dashboard Operacional | http://localhost:8000/dashboard/adidas/operations/ |

> 💡 El dashboard operacional es la parte más interesante del sistema. Usa el tenant `adidas` como punto de entrada para ver KPIs, colas SUNAT y métricas de integraciones.

---

## Credenciales Demo

El comando `seed_data` genera automáticamente un entorno operacional completo. No necesitas crear usuarios manualmente.

### Superusuario

| Campo | Valor |
| :--- | :--- |
| Email | `superadmin@nexus.com` |
| Password | `nexus_super1234` |

### Organizaciones Demo (Tenants)

El sistema crea 5 tenants independientes con datos completamente aislados entre sí:

| Organización | Slug |
| :--- | :--- |
| Tienda Principal | `tienda-principal` |
| Nike | `nike` |
| Adidas | `adidas` |
| Minorista | `minorista` |
| Mykonos Shop | `mykonos-shop` |

Cada tenant incluye su propio catálogo, clientes, inventario, pedidos multiestado, pagos, facturación mock SUNAT y datos analíticos operacionales. Ningún tenant puede ver los datos de otro — esto es el multi-tenancy en acción.

---

## Instalación con Docker (Recomendada)

### 1. Clonar el repositorio

```bash
git clone https://github.com/Sublian/nexus-oms-django.git
cd nexus-oms-django
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` y ajusta como mínimo estas variables:

```env
SECRET_KEY=<tu-clave-secreta>
DEBUG=True
DATABASE_URL=postgres://nexus_user:nexus_pass@db:5432/nexus_db
REDIS_URL=redis://redis:6379/0
CELERY_TASK_ALWAYS_EAGER=False
```

Para generar un `SECRET_KEY` seguro:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

> ⚠️ Nunca subas `.env` al repositorio. Está incluido en `.gitignore` por defecto.

### 3. Levantar servicios

```bash
docker compose up --build -d
```

Esto levanta el stack completo:

| Servicio | Descripción |
| :--- | :--- |
| `web` | Django + servidor de desarrollo Gunicorn |
| `worker` | Worker de Celery para tareas asíncronas |
| `db` | PostgreSQL 17 |
| `redis` | Redis 7 — broker de Celery y caché |

### 4. Aplicar migraciones

```bash
docker compose exec web python manage.py migrate
```

### 5. Cargar datos demo

```bash
docker compose exec web python manage.py seed_data --orders 50
```

### 6. Verificar que todo esté corriendo

```bash
docker compose ps
```

Todos los servicios deben aparecer en estado `running`. Si alguno falla, revisa la sección de [Troubleshooting](#troubleshooting).

---

## Instalación sin Docker

Útil para debugging más directo o entornos donde Docker no está disponible. Requiere **PostgreSQL 17** y **Redis 7** corriendo localmente.

### 1. Clonar y crear entorno virtual

```bash
git clone https://github.com/Sublian/nexus-oms-django.git
cd nexus-oms-django
python -m venv .venv
```

Activar el entorno:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar `.env`

```bash
cp .env.example .env
```

Ejemplo para entorno local:

```env
DATABASE_URL=postgres://nexus_user:nexus_pass@localhost:5432/nexus_db
REDIS_URL=redis://localhost:6379/0
```

### 4. Crear base de datos

Conecta a PostgreSQL y ejecuta:

```sql
CREATE USER nexus_user WITH PASSWORD 'nexus_pass';
CREATE DATABASE nexus_db OWNER nexus_user;
```

### 5. Aplicar migraciones

```bash
python manage.py migrate
```

### 6. Cargar datos demo

```bash
python manage.py seed_data --orders 50
```

### 7. Levantar Django

```bash
python manage.py runserver
```

### 8. Levantar Celery (terminal separada)

Celery es necesario para que funcionen las tareas asíncronas: facturación, reintentos SUNAT, notificaciones.

```bash
celery -A config worker --loglevel=info
```

---

## Seed Data — Datos Demo

El comando `seed_data` no solo crea datos de prueba básicos — genera un entorno operacional completo con distribución temporal realista para que el dashboard y las métricas tengan sentido desde el primer momento.

### ¿Qué genera por cada tenant?

- Productos, categorías, stock y almacenes
- Clientes con datos de contacto
- Pedidos en múltiples estados
- Pagos asociados a pedidos
- Facturas electrónicas mock (flujo SUNAT completo)
- Cola de sincronización SUNAT mock
- Logs de integraciones externas
- Métricas operacionales
- Datos contables demo

### Distribución temporal

Las órdenes se distribuyen automáticamente en los **últimos 60 días**. Esto es importante para que el dashboard operacional muestre series temporales reales, KPIs con tendencias y filtros de fecha funcionales — no datos agrupados en un solo día.

### Estados generados

**Pedidos**

| Estado | Significado |
| :--- | :--- |
| `PAID` | Pago confirmado |
| `SHIPPED` | En tránsito |
| `DELIVERED` | Entrega confirmada |
| `COMPLETED` | Ciclo completo |

**Facturación electrónica**

| Estado | Significado |
| :--- | :--- |
| `pending` | Esperando sincronización |
| `accepted` | Aceptada por SUNAT |
| `rejected` | Rechazada por SUNAT |
| `failed` | Error del proveedor |

**Cola SUNAT**

| Estado | Significado |
| :--- | :--- |
| `pending` | En cola de envío |
| `processing` | Siendo procesada |
| `completed` | Sincronizada exitosamente |
| `dead_letter` | Error terminal — requiere intervención |
| `exhausted` | Reintentos agotados |

### Ejemplos de uso

```bash
# Carga mínima (desarrollo rápido)
python manage.py seed_data --orders 5 --clients 3

# Carga estándar (recomendada)
python manage.py seed_data --orders 50

# Carga pesada (pruebas de rendimiento)
python manage.py seed_data --orders 200 --clients 100
```

---

## Facturación Electrónica (Estado Actual)

Nexus OMS utiliza actualmente un **provider mock** compatible con el flujo SUNAT/Nubefact. Esto permite desarrollar y validar el pipeline completo sin depender de servicios externos reales.

El mock cubre:

- Simulación de pipelines operacionales reales
- Validación del dashboard y visibilidad de colas
- Generación de métricas representativas
- Pruebas de flujos de reintentos y dead letters
- Detección de inconsistencias contables
- Visualización de errores operacionales

La integración real con SUNAT/Nubefact se implementará mediante adaptadores desacoplados — el dominio no cambia, solo se reemplaza el adaptador.

---

## Dashboard Operacional

El dashboard operacional multi-tenant está disponible en:

```
/dashboard/<tenant>/operations/
```

Incluye KPIs de facturación, tasa de aceptación SUNAT, profundidad de la cola de sincronización, dead letters, estado de integraciones externas, error rate por proveedor, latencia promedio, consistencia contable, series temporales y filtros de fecha.

> 💡 Usa `adidas` como tenant de prueba — el seed genera el volumen más representativo para ese slug por defecto.

---

## Testing

```bash
# Suite completa
docker compose exec web pytest

# Con cobertura
docker compose exec web pytest --cov
```

---

## Comandos Útiles

| Acción | Comando |
| :--- | :--- |
| Ver logs en tiempo real | `docker compose logs -f` |
| Detener el stack | `docker compose down` |
| Reiniciar servicios | `docker compose restart` |
| Django shell | `docker compose exec web python manage.py shell` |
| Ejecutar tests | `docker compose exec web pytest` |
| Coverage | `docker compose exec web pytest --cov` |
| Crear migraciones | `docker compose exec web python manage.py makemigrations` |
| Aplicar migraciones | `docker compose exec web python manage.py migrate` |

---

## Troubleshooting

### PostgreSQL no inicia

Suele ocurrir si hay un volumen corrupto de una sesión anterior.

```bash
docker compose down -v
docker compose up --build
```

### Redis: connection refused

```bash
docker compose ps
```

Verifica que el servicio `redis` aparezca como `running`. Si no, revisa los logs:

```bash
docker compose logs redis
```

### Migraciones inconsistentes

```bash
docker compose exec web python manage.py migrate
```

Si el problema persiste, puede haber migraciones en conflicto. Revisa `docker compose logs web` para ver el error específico.

### El dashboard aparece vacío

El dashboard requiere datos generados por `seed_data`. Si está vacío, ejecuta:

```bash
docker compose exec web python manage.py seed_data --orders 50
```

---

## Estructura del Proyecto

```text
nexus-oms-django/
├── src/
│   ├── domain/          # Modelos y lógica de negocio
│   ├── application/     # Casos de uso y servicios de analytics
│   ├── infrastructure/  # Celery, adapters, providers
│   └── interfaces/      # DRF API + vistas HTMX
│
├── config/              # Django settings + configuración Celery
├── docs/                # ADRs, roadmap y documentación
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Notas para Producción

> ⚠️ Esta guía es para entorno de desarrollo. Para producción, considera lo siguiente:

- `DEBUG=False` obligatorio
- Servir con **Gunicorn** detrás de **Nginx**
- Usar **PostgreSQL administrado** (RDS, Supabase, etc.)
- **Redis persistente** con AOF o RDB habilitado
- Variables de entorno gestionadas de forma segura (no archivos `.env` en el servidor)

---

## Documentación Relacionada

| Documento | Descripción |
| :--- | :--- |
| [`README.md`](../README.md) | Overview técnico del proyecto (inglés) |
| [`docs/README.es.md`](README.es.md) | README completo en español con contexto y decisiones |
| [`docs/operational_roadmap.md`](operational_roadmap.md) | Roadmap operacional y prioridades |
| [`docs/architecture.md`](architecture.md) | Arquitectura y decisiones técnicas (ADRs) |
| [`docs/adrs/`](adrs/) | Architecture Decision Records individuales |