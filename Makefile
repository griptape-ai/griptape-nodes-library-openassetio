# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
SHELL := /bin/bash

LIBRARY_JSON := griptape-nodes-library.json

.PHONY: version/get
version/get: ## Get version.
	@jq -r '.metadata.library_version' $(LIBRARY_JSON)

.PHONY: version/set
version/set: ## Set version. Usage: make version/set v=1.2.3
	@jq --arg v "$(v)" '.metadata.library_version = $$v' $(LIBRARY_JSON) > $(LIBRARY_JSON).tmp
	@mv $(LIBRARY_JSON).tmp $(LIBRARY_JSON)
	@make version/commit

.PHONY: version/patch
version/patch: ## Bump patch version.
	@CURRENT=$$(make version/get); \
	IFS='.' read -r major minor patch <<< "$$CURRENT"; \
	NEW_VERSION="$${major}.$${minor}.$$((patch + 1))"; \
	jq --arg v "$$NEW_VERSION" '.metadata.library_version = $$v' $(LIBRARY_JSON) > $(LIBRARY_JSON).tmp; \
	mv $(LIBRARY_JSON).tmp $(LIBRARY_JSON); \
	echo "Bumped to $$NEW_VERSION"
	@make version/commit

.PHONY: version/minor
version/minor: ## Bump minor version.
	@CURRENT=$$(make version/get); \
	IFS='.' read -r major minor patch <<< "$$CURRENT"; \
	NEW_VERSION="$${major}.$$((minor + 1)).0"; \
	jq --arg v "$$NEW_VERSION" '.metadata.library_version = $$v' $(LIBRARY_JSON) > $(LIBRARY_JSON).tmp; \
	mv $(LIBRARY_JSON).tmp $(LIBRARY_JSON); \
	echo "Bumped to $$NEW_VERSION"
	@make version/commit

.PHONY: version/major
version/major: ## Bump major version.
	@CURRENT=$$(make version/get); \
	IFS='.' read -r major minor patch <<< "$$CURRENT"; \
	NEW_VERSION="$$((major + 1)).0.0"; \
	jq --arg v "$$NEW_VERSION" '.metadata.library_version = $$v' $(LIBRARY_JSON) > $(LIBRARY_JSON).tmp; \
	mv $(LIBRARY_JSON).tmp $(LIBRARY_JSON); \
	echo "Bumped to $$NEW_VERSION"
	@make version/commit

.PHONY: version/commit
version/commit: ## Commit version.
	@git add $(LIBRARY_JSON)
	@git commit -m "chore: bump v$$(make version/get)"

.PHONY: version/publish
version/publish: ## Create and push git tags.
	@git fetch --tags --force
	@git tag "v$$(make version/get)"
	@git tag stable -f
	@git push origin "v$$(make version/get)"
	@git push -f origin stable

.PHONY: deps/sync
deps/sync: ## Sync pip_dependencies in the library JSON from pyproject.toml.
	@uv run python -c "\
import tomllib, json; \
pyproject = tomllib.load(open('pyproject.toml', 'rb')); \
deps = [d for d in pyproject['project']['dependencies'] if not d.startswith('griptape-nodes')]; \
lib = json.load(open('$(LIBRARY_JSON)')); \
lib['metadata'].setdefault('dependencies', {})['pip_dependencies'] = deps; \
open('$(LIBRARY_JSON)', 'w').write(json.dumps(lib, indent=4) + '\n'); \
print(f'Synced {len(deps)} dependencies to $(LIBRARY_JSON)')"

.PHONY: install
install: ## Install all dependencies.
	@make install/all

.PHONY: install/core
install/core: deps/sync ## Install core dependencies.
	@uv sync

.PHONY: install/all
install/all: deps/sync ## Install all dependencies.
	@uv sync --all-groups --all-extras

.PHONY: install/dev
install/dev: ## Install dev dependencies.
	@uv sync --group dev

.PHONY: install/hooks
install/hooks: ## Install pre-commit hooks.
	@uv run pre-commit install

.PHONY: lint
lint: ## Lint project.
	@uv run ruff check --fix
	@uv run pydoclint .

.PHONY: format
format: ## Format project.
	@uv run ruff format
	@uv run docstrfmt .
	@uv run mdformat *.md griptape_nodes_library_openassetio/ tests/ .github/

.PHONY: fix
fix: ## Fix project.
	@make format
	@uv run ruff check --fix --unsafe-fixes

.PHONY: test
test: ## Run tests.
	@uv run pytest tests/

.PHONY: test/coverage
test/coverage: ## Run tests with branch coverage.
	@uv run slipcover --branch --source griptape_nodes_library_openassetio --fail-under 90 -m pytest

.PHONY: check
check: check/format check/lint check/types check/json ## Run all checks.

.PHONY: pre-commit
pre-commit: ## Run pre-commit hooks on all files.
	@uv run pre-commit run --all-files

.PHONY: check/format
check/format:
	@uv run ruff format --check
	@uv run docstrfmt --check .
	@uv run mdformat --check *.md griptape_nodes_library_openassetio/ tests/ .github/

.PHONY: check/lint
check/lint:
	@uv run ruff check .
	@uv run pydoclint .

.PHONY: check/types
check/types:
	@uv run pyright .

.PHONY: check/json
check/json: ## Validate JSON files.
	@echo "Checking JSON files..."
	@find . -name "*.json" -type f \
		! -path "./.venv/*" \
		! -path "./node_modules/*" \
		-exec sh -c 'jq empty "{}" > /dev/null 2>&1 || (echo "Invalid JSON: {}" && exit 1)' \;

.DEFAULT_GOAL := help
.PHONY: help
help: ## Print Makefile help text.
	@# Matches targets with a comment in the format <target>: ## <comment>
	@# then formats help output using these values.
	@grep -E '^[a-zA-Z_\/-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	| awk 'BEGIN {FS = ":.*?## "}; \
		{printf "\033[36m%-12s\033[0m%s\n", $$1, $$2}'
