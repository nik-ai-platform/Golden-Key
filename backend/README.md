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

	Required variables: `DATABASE_URL`, `SECRET_KEY`, `JWT_SECRET`, `OPENAI_API_KEY`, `SPORTSBOOK_API_KEYS`, `REDIS_URL`, `SMTP_SETTINGS`.

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

## Authorization Matrix

All role-based authorization denials return the same payload:

```json
{
  "detail": "Insufficient permissions"
}
```

| Endpoint | Viewer | Analyst | Admin |
| --- | --- | --- | --- |
| `GET /api/v1/dashboard` | ✅ | ✅ | ✅ |
| `GET /api/v1/predictions/{game_id}` | ❌ | ✅ | ✅ |
| `POST /api/v1/imports/{sport}` | ❌ | ✅ | ✅ |
| `GET /api/v1/backtests/*` (planned) | ❌ | ✅ | ✅ |
| `GET /api/v1/users/*` (planned) | ❌ | ❌ | ✅ |

Notes:

- `backtests` and `users` routes are not implemented yet, but target policy is documented here for frontend planning.
- Any endpoint protected with `require_viewer`, `require_analyst`, or `require_admin` follows the same matrix semantics.

## OpenAPI Authorization Reference

Swagger/OpenAPI auth flow uses OAuth2 bearer with this token URL:

- `POST /api/v1/auth/login`

Dependency guards and role policy mapping:

| Dependency | Allowed Roles | Typical Use |
| --- | --- | --- |
| `require_viewer` | `viewer`, `analyst`, `admin` | Read-only dashboards, analytics, intelligence views |
| `require_analyst` | `analyst`, `admin` | Prediction and import workflows |
| `require_admin` | `admin` | Administrative/management operations |

Example endpoint annotations:

- Router-level guard:

	```python
	router = APIRouter(
			prefix="/imports",
			tags=["Imports"],
			dependencies=[Depends(require_analyst)],
	)
	```

- Endpoint-level guard:

	```python
	@router.get("/{team_id}/intelligence")
	def get_team_intelligence(
			team_id: int,
			_current_user=Depends(require_viewer),
			db: Session = Depends(get_db),
	):
			...
	```

Contract for role-denied requests remains stable:

```json
{
	"detail": "Insufficient permissions"
}
```

## Prediction Contract Note

`GET /api/v1/predictions/{game_id}` is a single-game prediction snapshot endpoint.

- It is not a real-time analytics feed.
- Returned NPI values are model outputs, not live scoreboard data.
- For historical and aggregate analytics, use `/api/v1/analytics/*` endpoints.
