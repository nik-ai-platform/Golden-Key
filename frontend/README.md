# Frontend

Production React frontend for the Nik AI Platform.

## Stack

- React
- TypeScript
- Vite
- React Router
- TanStack Query
- Axios
- Recharts
- Material UI

## Folder Structure

```
src/
	api/
	auth/
	components/
	hooks/
	layouts/
	pages/
	routes/
	services/
	types/
	utils/
```

## Implemented Sprint Pages

- Login
- Dashboard
- Predictions
- Games
- Team Intelligence
- Analytics

## Recommended Integration Order

Use this order when validating changes or onboarding new contributors:

1. Login
2. Dashboard
3. Predictions
4. Games
5. Team Intelligence
6. Analytics

This sequence gets a usable app quickly and validates API contracts incrementally.

## Auth and Route Protection

- JWT is stored once via `auth/tokenStorage.ts`
- Axios client in `api/client.ts` injects `Authorization` header
- Protected pages are routed through `components/ProtectedRoute.tsx`

## Local Development

From this folder:

```powershell
npm install
npm run dev
```

Optional API base URL override:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000/api/v1"
```

## 5-Minute Local QA Runbook

Use two terminals from the repository root for a fast manual pass.

Terminal A (backend):

```powershell
Set-Location .\backend
py -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Terminal B (frontend):

```powershell
Set-Location .\frontend
$env:VITE_API_BASE_URL="http://127.0.0.1:8001/api/v1"
npm run dev
```

Then validate in this order:

1. Login: authenticate and verify redirect to Dashboard.
2. Dashboard: confirm key cards and confidence summary load.
3. Predictions: apply winner filter, min confidence, and sorting.
4. Games: verify upcoming, live, and completed sections.
5. Team Intelligence: confirm metrics and team switch behavior.
6. Analytics: confirm charts/cards render and data updates.

Quick friction check before release:

1. Retry behavior: briefly stop backend and click Retry on a failing page.
2. Role behavior: test viewer and analyst/admin access boundaries.
3. Responsiveness: check a narrow mobile viewport and tablet width.

## Executive Intelligence responsive QA

The dashboard uses the existing theme and MUI breakpoints: mobile below 600px
(`sm`), with table-oriented market and game panels starting at 900px (`md`).
Check 320px, 390px, 600px, 900px, and desktop widths in both theme modes.

- Mobile headings and Best Bet spacing are compact; probability and confidence
  remain separate, two-column metrics. View Analysis is primary; Save Pick retains
  its existing saved, pending, and error behavior.
- Model Intelligence totals show the full muted matchup before the prominent
  OVER/UNDER selection. Spread and moneyline selections retain their supplied labels.
- Upcoming Games uses mobile matchup cards with team-associated spread/moneyline
  and a single game-total row. Missing odds/scores remain dashes; supplied scores,
  including zero, are displayed without introducing another API request.
- Mobile navigation retains all six destinations and scrolls horizontally.
  Main content reserves 88px plus the iPhone bottom safe-area inset.

Focused regression command from the repository root:

```powershell
npm --prefix frontend test -- --run tests/frontend/dashboard-hero.test.tsx tests/frontend/product-dashboard.test.tsx tests/frontend/mobile-nav.test.tsx tests/frontend/product-navigation.test.tsx tests/frontend/pick-metrics.test.tsx tests/frontend/save-pick-button.test.tsx
```

## Production Build

```powershell
npm run build
```

## E2E Smoke Tests

Playwright smoke coverage includes:

- Anonymous user redirected to login
- Login success redirects to dashboard
- Authenticated dashboard metrics render

Run:

```powershell
npx playwright install chromium
npm run test:e2e
```

## Manual Beta Checklist

Once Login and Dashboard are working, run a short manual pass before Docker/deploy:

1. Login with each role and confirm route access behavior.
2. Open Predictions and test winner/confidence filter plus sort controls.
3. Open Games and verify upcoming/live/completed grouping is sensible.
4. Open Team Intelligence and verify key metrics render (momentum, trend, strength, offense, defense, home/away record).
5. Open Analytics and confirm cards/charts load (accuracy, confidence buckets, model comparison, trends, backtesting).
6. Force a temporary API failure (or stop backend) and confirm retry flows recover.

Any friction found here should be fixed before deployment to reduce beta rework.

## Docker

Frontend Docker image uses multi-stage build:

1. Build React app in Node
2. Serve static `dist` through Nginx

With root compose:

```powershell
docker compose up --build
```
