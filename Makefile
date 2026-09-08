# Comandos de desarrollo. Todo asume el entorno virtual en .venv.
PY := .venv/bin/python
PIP := uv pip

.DEFAULT_GOAL := ayuda

.PHONY: ayuda entorno migrar revertir esquema pruebas pruebas-rapidas lint formato tipos verificar limpiar

ayuda:  ## Lista los comandos disponibles
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

entorno:  ## Crea el entorno virtual e instala dependencias
	uv venv --python 3.11 .venv
	. .venv/bin/activate && $(PIP) install -e ".[dev]"

migrar:  ## Aplica todas las migraciones
	.venv/bin/alembic upgrade head

revertir:  ## Revierte la última migración
	.venv/bin/alembic downgrade -1

esquema:  ## Verifica que los modelos y las migraciones no divergieron
	.venv/bin/alembic check

pruebas:  ## Ejecuta la suite completa
	$(PY) -m pytest

pruebas-rapidas:  ## Ejecuta solo lo que no necesita PostgreSQL ni red
	$(PY) -m pytest -m "not integracion and not red"

lint:  ## Revisa estilo
	.venv/bin/ruff check src tests

formato:  ## Formatea el código
	.venv/bin/ruff format src tests
	.venv/bin/ruff check --fix src tests

tipos:  ## Verifica tipos
	.venv/bin/mypy

verificar: lint tipos esquema pruebas  ## Todo lo que corre CI

limpiar:  ## Borra artefactos de construcción y caches
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
