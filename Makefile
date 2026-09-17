# /!\ DEVELOPMENT ONLY — do not use this Makefile in production.
#
# 1. Variables live in VARIABLES
# 2. Rules live in RULES, grouped by service
# 3. Rules are sorted alphabetically within a section
# 4. .PHONY sits after the corresponding rule

# ==============================================================================
# VARIABLES

ESC := $(shell printf '\033')
BOLD := $(ESC)[1m
RESET := $(ESC)[0m
GREEN := $(ESC)[1;32m

ifeq ($(OS),Windows_NT)
DOCKER_USER         := 0:0
else
DOCKER_UID          := $(shell id -u)
DOCKER_GID          := $(shell id -g)
DOCKER_USER         := $(DOCKER_UID):$(DOCKER_GID)
endif

COMPOSE             = DOCKER_USER=$(DOCKER_USER) docker compose
COMPOSE_RUN         = $(COMPOSE) run --rm
COMPOSE_RUN_DOCS    = $(COMPOSE_RUN) docs-app
COMPOSE_RUN_MEET    = $(COMPOSE_RUN) meet-app
COMPOSE_RUN_DICTAPHONE = $(COMPOSE_RUN) dictaphone-app
MANAGE_DOCS         = $(COMPOSE_RUN_DOCS) python manage.py
MANAGE_MEET         = $(COMPOSE_RUN_MEET) python manage.py
MANAGE_DICTAPHONE   = $(COMPOSE_RUN_DICTAPHONE) python manage.py

REPOS               = dictaphone docs meet

# ==============================================================================
# RULES

default: help

data/media:
	@mkdir -p data/media data/docs-static data/meet-static data/dictaphone-static data/livekit-out

# -- Project

bootstrap: ## clone repos if needed, build images, migrate DBs, start the stack
bootstrap: \
# 	clone
	data/media \
	build \
	pull \
	migrate \
	superuser \
	run
	@echo ""
	@echo "$(GREEN)La Suite interop stack is up.$(RESET)"
	@echo "  Docs:        http://localhost:3000"
	@echo "  Meet:        http://localhost:3001"
	@echo "  Dictaphone:  http://localhost:3002"
	@echo "  Keycloak:    http://localhost:8083  (admin/admin)"
	@echo "  MinIO:       http://localhost:9001  (lasuite/password)"
	@echo ""
	@echo "Shared Keycloak user (all three realms): lasuite / lasuite"
.PHONY: bootstrap

clone: ## clone Docs, Meet and Dictaphone if they are missing
#	@test -d docs/.git || git clone --depth 1 https://github.com/suitenumerique/docs.git
#	@test -d meet/.git || git clone --depth 1 https://github.com/suitenumerique/meet.git
#	@test -d dictaphone/.git || git clone --depth 1 https://github.com/suitenumerique/dictaphone.git
	@$(MAKE) patch-upstreams
	@$(MAKE) prepare-realms
	@$(MAKE) docs-mails
.PHONY: clone

docs-mails: ## generate Docs email templates required by create-for-owner
	@docker run --rm -u $(DOCKER_USER) -v "$(CURDIR)/docs/src:/src" -w /src/mail node:22 sh -c "yarn install --frozen-lockfile && yarn build"
.PHONY: docs-mails

patch-upstreams: ## apply local CSRF and Albert STT patches on the cloned repos
	@python3 scripts/patch_upstreams.py
.PHONY: patch-upstreams

prepare-realms: ## rebuild Keycloak realm files from the cloned repos
	@python3 scripts/prepare_realms.py
.PHONY: prepare-realms

# -- Docker

build: ## build application images
	@$(COMPOSE) build docs-app docs-frontend docs-y-provider meet-app meet-frontend summary meet-metadata-collector dictaphone-app dictaphone-frontend
.PHONY: build

pull: ## pre-pull third-party images (LiveKit, Docspec, Keycloak, …)
	@$(COMPOSE) pull --ignore-buildable --policy missing
.PHONY: pull

config: ## render the merged compose file (sanity check)
	@$(COMPOSE) config >/dev/null && echo "compose config: OK"
.PHONY: config

down: ## stop and remove containers and networks
	@$(COMPOSE) down --remove-orphans
.PHONY: down

logs: ## follow logs for all services
	@$(COMPOSE) logs -f
.PHONY: logs

ps: ## show running services
	@$(COMPOSE) ps
.PHONY: ps

run: ## start the full interop stack
	@$(COMPOSE) up -d --remove-orphans
.PHONY: run

stop: ## stop the stack without removing containers
	@$(COMPOSE) stop
.PHONY: stop

# -- Database

migrate: ## run Django migrations for Docs, Meet and Dictaphone
migrate: migrate-docs migrate-meet migrate-dictaphone
.PHONY: migrate

infra: ## start shared PostgreSQL, Redis and MinIO (and create buckets)
	@$(COMPOSE) up -d postgresql redis minio mailcatcher --wait
	@$(COMPOSE) up --no-deps createbuckets
.PHONY: infra

migrate-docs: ## migrate the Docs database
	@echo "$(BOLD)Migrating Docs$(RESET)"
	@$(MAKE) infra
	@$(MANAGE_DOCS) migrate
.PHONY: migrate-docs

migrate-meet: ## migrate the Meet database
	@echo "$(BOLD)Migrating Meet$(RESET)"
	@$(MAKE) infra
	@$(MANAGE_MEET) migrate
.PHONY: migrate-meet

migrate-dictaphone: ## migrate the Dictaphone database
	@echo "$(BOLD)Migrating Dictaphone$(RESET)"
	@$(MAKE) infra
	@$(MANAGE_DICTAPHONE) migrate
.PHONY: migrate-dictaphone

superuser: ## create admin@example.com / admin on each backend
	@echo "$(BOLD)Creating Django superusers$(RESET)"
	@$(MANAGE_DOCS) createsuperuser --email admin@example.com --password admin || true
	@$(MANAGE_MEET) createsuperuser --email admin@example.com --password admin || true
	@$(MANAGE_DICTAPHONE) createsuperuser --email admin@example.com --password admin || true
.PHONY: superuser

demo: ## load demo content into each app
	@$(MANAGE_DOCS) create_demo || true
	@$(MANAGE_MEET) create_demo || true
	@$(MANAGE_DICTAPHONE) create_demo || true
.PHONY: demo

# -- Help

help: ## display available targets
	@echo "$(BOLD)La Suite interop$(RESET)"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-22s %s\n", $$1, $$2}'
.PHONY: help
