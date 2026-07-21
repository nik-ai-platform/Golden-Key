# Backend

Backend services and API layer for the nik-ai-platform.

## Structure

- `api/` - API endpoints and handlers
- `services/` - Business logic
- `models/` - Data models
- `migrations/` - Database migrations
- `tests/` - Test suite
- `config/` - Configuration files

## Setup

1. Copy environment variables:

	```powershell
	Copy-Item .env.example .env
	```

2. Start PostgreSQL with Docker (host port `5433` -> container `5432`):

	```powershell
	Set-Location ..
	docker compose up -d postgres
	Set-Location backend
	```

3. Install Python dependencies:

	```powershell
	py -m pip install -r requirements.txt
	```

4. Create database tables:

	```powershell
	py -c "from app.database.base import Base; from app.database.session import engine; import app.models; Base.metadata.create_all(bind=engine)"
	```

5. Run the API:

	```powershell
	py -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
	```

6. Verify endpoints:

	- `http://127.0.0.1:8000/openapi.json`
	- `http://127.0.0.1:8000/api/v1/teams/`
