FROM python:3.12-slim

# Evitar prompts de configuración durante la instalación
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Instalación optimizada de dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dependencias base y DB
    libpq-dev \
    gcc \
    libc6-dev \
    # Dependencias esenciales de WeasyPrint (Pango + Cairo + GObject)
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libharfbuzz0b \
    libffi-dev \
    shared-mime-info \
    # Fuentes básicas (necesarias para que el PDF no salga con cuadritos)
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000