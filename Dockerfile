# Imagen de la aplicación. No trae credenciales: la configuración operativa
# entra por variables de entorno del despliegue, y los secretos por el gestor de
# secretos del destino.
#
# Dos etapas para que la imagen final no cargue con las herramientas de
# compilación: lo que se despliega es lo que hace falta para servir.
FROM python:3.11-slim AS construccion

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# psycopg necesita las cabeceras de libpq para compilar; en la imagen final solo
# hace falta la biblioteca.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install .

FROM python:3.11-slim AS aplicacion

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 acij

COPY --from=construccion /opt/venv /opt/venv

WORKDIR /app
# Las migraciones viajan con la imagen: el esquema que la aplicación espera es
# el que sabe aplicar, y separarlos deja abierta la puerta a desplegar código
# contra un esquema que no le corresponde.
COPY alembic.ini ./
COPY src/backend_normativo/migrations ./src/backend_normativo/migrations
COPY docs/paquete ./docs/paquete

USER acij

# Cloud Run y compañía inyectan el puerto; 8080 es el que esperan por defecto.
ENV PORT=8080
EXPOSE 8080

# Un solo proceso por contenedor: la concurrencia se agrega con instancias, y el
# presupuesto de conexiones a la base se calcula sobre esa cuenta.
CMD ["sh", "-c", "exec uvicorn backend_normativo.api.app:app --host 0.0.0.0 --port ${PORT}"]
