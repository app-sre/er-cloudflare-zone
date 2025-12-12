.DEFAULT_GOAL := test

CONTAINER_ENGINE ?= $(shell which podman >/dev/null 2>&1 && echo podman || echo docker)

.PHONY: format
format:
	uv run ruff check
	uv run ruff format

.PHONY: test
test:
	uv run ruff check --no-fix
	uv run ruff format --check
	uv run mypy
	uv run pytest -vv --cov=er_cloudflare_zone --cov-report=term-missing --cov-report xml

.PHONY: build
build:
	$(CONTAINER_ENGINE) build -t er-cloudflare-zone:test --target test .

.PHONY: dev-env
dev-env:
	uv sync

.PHONY: providers-lock
providers-lock:
	terraform -chdir=module providers lock -platform=linux_amd64 -platform=linux_arm64 -platform=darwin_amd64 -platform=darwin_arm64
