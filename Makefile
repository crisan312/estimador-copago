up:
	cp -n .env.example .env || true
	docker compose up --build

down:
	docker compose down

dev-api:
	cd backend && uvicorn main:app --reload --port 8000

dev-web:
	cd frontend && npm run dev

logs:
	docker compose logs -f

shell-api:
	docker compose exec api bash
