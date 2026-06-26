.PHONY: start stop rebuild logs test lint clean

# Start all containers in detached mode
start:
	docker compose up -d

# Stop all containers
stop:
	docker compose down -v

# Rebuild and start all containers
rebuild:
	docker compose up -d --build

# Stream active logs
logs:
	docker compose logs -f

# Run backend test suite via pytest inside container
test:
	docker compose exec backend pytest

# Run backend ruff code validation check
lint:
	docker compose exec backend ruff check .
	docker compose exec frontend npm run lint

# Clean temporary system caches
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
