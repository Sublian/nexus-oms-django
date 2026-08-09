#!/bin/sh
set -e

# Aplica migraciones automáticamente SOLO cuando RUN_MIGRATIONS=true
# (el servicio web de producción lo activa; worker/beat y dev no).
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo ">> Aplicando migraciones de base de datos..."
  python manage.py migrate --noinput
fi

# exec: reemplaza el shell para que la señal SIGTERM llegue directo al proceso
exec "$@"
