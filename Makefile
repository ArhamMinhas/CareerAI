.PHONY: help install lint format typecheck test build clean docker-build docker-push deploy

# Default target
help:
	@echo "CareerAI — CI/CD & Development Tasks"
	@echo ""
	@echo "Setup:"
	@echo "  make install           Install all dependencies (npm + pip)"
	@echo "  make pre-commit-setup  Set up pre-commit hooks"
	@echo ""
	@echo "Quality:"
	@echo "  make lint              Lint all code (frontend + backend)"
	@echo "  make format            Format all code (frontend + backend)"
	@echo "  make typecheck         Type check all code (tsc + mypy)"
	@echo "  make test              Run all tests (frontend + backend)"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  make build             Build all apps (web + api)"
	@echo "  make docker-build      Build Docker images locally"
	@echo "  make docker-push       Push images to registry"
	@echo "  make deploy-staging    Deploy to staging"
	@echo "  make deploy-prod       Deploy to production"
	@echo ""
	@echo "Local Development:"
	@echo "  make dev               Start local dev environment (docker-compose up)"
	@echo "  make dev-stop          Stop local dev environment"
	@echo "  make dev-logs          Show logs from local dev environment"
	@echo "  make db-migrate        Run database migrations"
	@echo "  make db-seed           Seed database with test data"
	@echo ""
	@echo "Cleaning:"
	@echo "  make clean             Remove build artifacts"
	@echo "  make clean-all         Remove everything including node_modules, venv"

install:
	npm ci
	cd apps/api && pip install -r requirements/dev.txt

pre-commit-setup:
	pip install pre-commit
	pre-commit install
	@echo "✓ Pre-commit hooks installed"

lint: lint-frontend lint-backend

lint-frontend:
	npm run lint:web

lint-backend:
	cd apps/api && ruff check .

format: format-frontend format-backend

format-frontend:
	npm run lint:web -- --fix

format-backend:
	cd apps/api && ruff check . --fix && ruff format .

typecheck: typecheck-frontend typecheck-backend

typecheck-frontend:
	npm run typecheck:web

typecheck-backend:
	cd apps/api && mypy app

test: test-frontend test-backend

test-frontend:
	npm run test:web

test-backend:
	cd apps/api && pytest -v

build: build-frontend build-backend

build-frontend:
	npm run build:web

build-backend:
	@echo "Backend build not needed (FastAPI is interpreted)"

docker-build:
	docker build -f infrastructure/docker/Dockerfile.web -t careerai-web:latest .
	docker build -f infrastructure/docker/Dockerfile.api -t careerai-api:latest --target production .
	docker build -f infrastructure/docker/Dockerfile.worker -t careerai-worker:latest --target production .
	@echo "✓ Docker images built"

docker-push: docker-build
	docker tag careerai-web:latest $(DOCKER_REGISTRY)/careerai-web:latest
	docker tag careerai-api:latest $(DOCKER_REGISTRY)/careerai-api:latest
	docker tag careerai-worker:latest $(DOCKER_REGISTRY)/careerai-worker:latest
	docker push $(DOCKER_REGISTRY)/careerai-web:latest
	docker push $(DOCKER_REGISTRY)/careerai-api:latest
	docker push $(DOCKER_REGISTRY)/careerai-worker:latest
	@echo "✓ Docker images pushed"

deploy-staging:
	@echo "Triggering deployment to staging via GitHub Actions..."
	gh workflow run deploy.yml -f environment=staging

deploy-prod:
	@echo "Triggering deployment to production via GitHub Actions..."
	gh workflow run deploy.yml -f environment=production

dev:
	docker-compose -f infrastructure/docker/docker-compose.yml up -d
	@echo "✓ Local dev environment started"
	@echo "  - Web: http://localhost:3000"
	@echo "  - API: http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/docs"

dev-stop:
	docker-compose -f infrastructure/docker/docker-compose.yml down

dev-logs:
	docker-compose -f infrastructure/docker/docker-compose.yml logs -f

db-migrate:
	cd apps/api && alembic upgrade head

db-seed:
	@echo "Seeding database with test data..."
	cd apps/api && python -m app.scripts.seed_career_paths
	cd apps/api && python -m app.scripts.seed_jobs

clean:
	rm -rf apps/web/.next apps/web/dist
	rm -rf apps/api/__pycache__ apps/api/.pytest_cache
	rm -rf .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-all: clean
	rm -rf node_modules apps/web/node_modules
	rm -rf venv .venv
	rm -rf apps/api/.mypy_cache

.PHONY: ci-local
ci-local: lint typecheck test build
	@echo "✓ All CI checks passed locally"
