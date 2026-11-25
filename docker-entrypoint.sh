#!/bin/sh
# Arranque del contenedor. Render monta el disco persistente (DATA_DIR, p. ej. /var/data) como root:
# aquí, todavía como root, se le da al usuario de la app y luego la app corre SIN privilegios.
set -e

if [ "$(id -u)" = "0" ]; then
    if [ -n "$DATA_DIR" ]; then
        mkdir -p "$DATA_DIR"
        chown -R appuser:appuser "$DATA_DIR"
    fi
    exec setpriv --reuid=appuser --regid=appuser --init-groups "$@"
fi

exec "$@"
