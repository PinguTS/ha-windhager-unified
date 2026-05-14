# Local checks run inside Docker (see compose.yaml, Dockerfile.test).

DOCKER_COMPOSE ?= docker compose
SERVICE := test
RUN := $(DOCKER_COMPOSE) run --rm $(SERVICE)

.PHONY: help build test lint format-check format check ci shell install-git-hooks build-docs

help:
	@echo "Docker-backed targets (no host Python required):"
	@echo "  make build          Build the test image"
	@echo "  make test           pytest --tb=short -v"
	@echo "  make lint           ruff check"
	@echo "  make format-check   black --check"
	@echo "  make format         black (write)"
	@echo "  make check / ci     lint, format-check, then test"
	@echo "  make build-docs     Generate docs/integrator/rest-api.md and swagger-coverage.md"
	@echo "  make shell          Interactive shell in the test container"
	@echo "  make install-git-hooks  git config core.hooksPath .githooks"

build:
	$(DOCKER_COMPOSE) build $(SERVICE)

test:
	$(RUN) pytest --tb=short -v

lint:
	$(RUN) ruff check custom_components/windhager_unified tests

format-check:
	$(RUN) black --check --line-length 100 custom_components/windhager_unified tests

format:
	$(RUN) black --line-length 100 custom_components/windhager_unified tests

check: lint format-check test
ci: check

shell:
	$(DOCKER_COMPOSE) run --rm -it $(SERVICE) bash

build-docs:
	$(RUN) python scripts/build_docs.py

install-git-hooks:
	chmod +x .githooks/pre-commit
	git config core.hooksPath .githooks
	@echo "core.hooksPath set to .githooks (run from this repo clone)."
