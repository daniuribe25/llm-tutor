.PHONY: dev dev-backend dev-frontend

PY := .venv/bin/python
BACKEND_HOST := 127.0.0.1
BACKEND_PORT := 8000

# Run FastAPI and Next.js dev servers together (each reloads on file changes).
dev:
	$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	$(PY) -m uvicorn api.main:app --reload --host $(BACKEND_HOST) --port $(BACKEND_PORT)

dev-frontend:
	cd web && npm run dev
