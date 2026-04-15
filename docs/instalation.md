# Instalación — Nexus OMS

Guía de instalación local usando **Docker Compose** (método recomendado).

---

## Prerrequisitos

| Herramienta | Versión mínima |
|---|---|
| Git | cualquiera |
| Docker | 24+ |
| Docker Compose | v2+ |
| Python | 3.12+ *(solo para instalación sin Docker)* |

---

## Instalación con Docker (recomendado)

### 1. Clonar el repositorio

```bash
git clone https://github.com/Sublian/nexus-oms-django.git
cd nexus-oms-django
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` y ajustar como mínimo:

```env
# Generar una clave segura con:
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY=<tu-clave-secreta>

DEBUG=True

# Valores por defecto alineados con docker-compose.yml
DATABASE_URL=postgres://nexus_user:nexus_pass@db:5432/nexus_db
REDIS_URL=redis://redis:6379/0
CELERY_TASK_ALWAYS_EAGER=False
```

### 3. Levantar los servicios

```bash
docker compose up --build -d
```

Esto levanta 4 servicios: `db` (PostgreSQL 16), `redis` (Redis 7), `web` (Django en puerto 8000) y `worker` (Celery).

### 4. Aplicar migraciones

```bash
docker compose exec web python manage.py migrate
```

### 5. Crear superusuario (opcional)

```bash
docker compose exec web python manage.py createsuperuser
```

### 6. Acceder a la aplicación

- **App:** http://localhost:8000
- **Admin:** http://localhost:8000/admin

---

## Instalación sin Docker (entorno local)

> Requiere PostgreSQL 17 y Redis 7 instalados y corriendo localmente.

### 1. Clonar y crear entorno virtual

```bash
git clone https://github.com/Sublian/nexus-oms-django.git
cd nexus-oms-django

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env y apuntar DATABASE_URL / REDIS_URL a tu instancia local
```

Ejemplo para PostgreSQL local:

```env
DATABASE_URL=postgres://nexus_user:nexus_pass@localhost:5432/nexus_db
REDIS_URL=redis://localhost:6379/0
```

### 4. Crear base de datos en PostgreSQL

```sql
CREATE USER nexus_user WITH PASSWORD 'nexus_pass';
CREATE DATABASE nexus_db OWNER nexus_user;
```

### 5. Aplicar migraciones y levantar el servidor

```bash
python manage.py migrate
python manage.py createsuperuser   # opcional
python manage.py runserver
```

### 6. Levantar el worker de Celery (en otra terminal)

```bash
celery -A config worker --loglevel=info
```

---

## Data semilla (seed_data)

El comando `seed_data` carga datos de prueba realistas en la base de datos: organizaciones (tenants), categorías, productos, almacenes, clientes, órdenes y pagos. Es útil para explorar el sistema sin necesidad de cargar datos manualmente.

### Uso básico

```bash
# Con Docker
docker compose exec web python manage.py seed_data

# Sin Docker (entorno local)
python manage.py seed_data
```

Esto crea **5 organizaciones** de demostración con **30 órdenes** y **10 clientes** cada una (valores por defecto).

### Opciones disponibles

| Argumento | Tipo | Default | Descripción |
|---|---|---|---|
| `--orders` | int | `30` | Número de órdenes generadas por organización |
| `--clients` | int | `10` | Número de clientes generados por organización |

### Ejemplos

```bash
# Carga mínima: 5 órdenes y 3 clientes por organización
python manage.py seed_data --orders 5 --clients 3

# Carga grande: 100 órdenes y 50 clientes por organización
python manage.py seed_data --orders 100 --clients 50
```

### Datos que genera

El seed crea las siguientes organizaciones (tenants) con su catálogo propio:

| Organización | Slug | IGV | Catálogo |
|---|---|---|---|
| Tienda Principal | `tienda-principal` | 18% | 10 productos genéricos |
| Nike | `nike` | 15% | 10 productos genéricos |
| Adidas | `adidas` | 15% | 10 productos genéricos |
| Minorista | `minorista` | 12% | 10 productos genéricos |
| Mykonos Shop | `mykonos-shop` | 18% | 5 fragancias específicas |

Por cada organización también genera: un almacén central, una configuración de impuestos, un pool de clientes con DNI y datos de contacto aleatorios, y órdenes en estados `PAID`, `SHIPPED` o `DELIVERED` con fechas distribuidas en los últimos 60 días y pagos asociados (`CASH`, `CARD`, `TRANSFER`, `WALLET`).

> **Nota:** El comando usa `update_or_create`, por lo que puede ejecutarse múltiples veces sin duplicar registros base (organizaciones, productos, stock). Solo se acumulan las órdenes y clientes nuevos.

---

## Comandos útiles

| Acción | Comando |
|---|---|
| Ver logs en tiempo real | `docker compose logs -f` |
| Detener todos los servicios | `docker compose down` |
| Ejecutar tests | `docker compose exec web pytest` |
| Ver cobertura | `docker compose exec web pytest --cov` |
| Abrir shell de Django | `docker compose exec web python manage.py shell` |

---

## Estructura del proyecto

```
nexus-oms-django/
├── src/
│   ├── domain/          # Modelos y lógica de negocio
│   ├── application/     # Casos de uso
│   ├── infrastructure/  # Celery, AWS, adaptadores
│   └── interfaces/      # API REST (DRF) y vistas HTMX
├── config/              # Configuración de Django y Celery
├── docs/                # Documentación adicional y ADRs
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Notas

- El archivo `.env` **nunca** debe subirse al repositorio (ya está en `.gitignore`).
- En producción, establecer `DEBUG=False` y configurar un servidor Nginx frente a Gunicorn.
- Consulta la carpeta `docs/` para diagramas de arquitectura y decisiones de diseño (ADRs).
