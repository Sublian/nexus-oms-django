# syntax=docker/dockerfile:1

# ─────────────────────────────────────────────────────────────────────────────
# Nexus OMS — Imagen de producción
#
# Multi-stage build:
#   builder  → instala las dependencias (taller completo, se descarta)
#   runtime  → solo lo necesario para correr (ligera, sin compiladores)
# ─────────────────────────────────────────────────────────────────────────────

# Imagen base fijada a un parche concreto (bookworm: maduro y estable).
# requirements.txt es el lockfile (pip freeze): builds reproducibles.
FROM python:3.12.13-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Dependencias de COMPILACIÓN (gcc, headers). Solo existen en esta etapa.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libc6-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Virtualenv aislado: se copia entero a la etapa runtime
RUN python -m venv /opt/venv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH" \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Dependencias de RUNTIME — WeasyPrint (Pango/Cairo) + fuentes para PDFs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libharfbuzz0b \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

# Usuario sin privilegios: si la app se compromete, el intruso no es root
RUN addgroup --system --gid 1001 app \
    && adduser --system --uid 1001 --ingroup app app

COPY --chown=app:app . .
COPY --chown=app:app entrypoint.sh /app/entrypoint.sh

# Guarda: si el archivo se guardó con finales de línea Windows, los corrige
RUN sed -i 's/\r$//' /app/entrypoint.sh

USER app

EXPOSE 8000

# Por defecto arranca como servidor de producción.
# En desarrollo docker-compose sobreescribe el command con runserver.
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--access-logfile", "-"]
