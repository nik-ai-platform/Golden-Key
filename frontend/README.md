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

## Customer Metric Education

- The public `/how-it-works` route explains NPI, Model Probability, Confidence
  Rating, Projected Edge, Risk Level, publication, and responsible interpretation.
- Desktop navigation and the mobile navigation drawer include How It Works.
  The fixed mobile bottom navigation retains its six existing destinations.
- `src/data/predictionMetricEducation.ts` is the shared customer-copy source for
  the page and metric help dialogs. Every metric help dialog links to the page.
- NPI is market-specific; numeric Performance ranges are reporting buckets, not
  calibrated strength bands. No percentiles or predictive strength tiers are
  published. Confidence Rating displays without a percent suffix, while Model
  Probability retains one. Stored values and calculations are unchanged.

## Customer launch: Free Preview and Premium

- `/` is public product information. `/how-it-works`, `/terms`, `/privacy`,
  `/responsible-gaming`, `/disclaimer`, and `/support` are public. Legal copy is
  expressly an operational draft requiring attorney review; contact identity,
  mailbox ownership, jurisdiction and consumer-rights details are launch gates.
  The support mailto opens the customer's email application and sends nothing.
- `src/data/customerSupport.ts` centralizes the public support mailbox,
  `owner@bearahandllc.com`, for support and account-recovery links. Mailbox
  ownership, send/receive capability, staffing and two-factor setup remain
  operational checks, not claims established by this code.
- Authentication grants dashboard slate overview and `/profile`, not paid data.
  Free overview reads only `GET /api/v1/product/preview`:
  `{sport, count, games:[{game_id,sport,league,home_team,away_team,start_time,status}]}`.
  It does not render selections, odds, predictions or game-analysis links.
- `PremiumRoute` checks `GET /api/v1/subscriptions/me` (`active === true`) and
  explicitly permits authenticated admins. Loading, refetch and API errors
  fail closed. Games/details, saved picks, parlays and performance are gated.
  Role labels, profile's legacy `premium` flag, browser URLs and checkout
  success do not grant access. Server authorization remains authoritative.
- `GET /api/v1/subscriptions/plans` is the single pricing source:
  `{currency,trial_days,plans:[{id,name,amount_minor,interval}],premium_benefits}`.
  Currency is formatted using `Intl.NumberFormat`; no client-owned prices,
  price IDs or fees. Failed configuration disables plan purchase.
- `/profile?checkout=success` polls canonical subscription state up to ten
  times at two-second intervals, stops on active access, and offers an
  accessible refresh after timeout/error. Canceled/failed returns grant no
  access. Profile/billing remain reachable for free or expired accounts and
  billing management is shown for existing Stripe relationships.
- Verification resend uses neutral `POST /auth/email-verification {email}`;
  token confirmation uses `/auth/email-verification/confirm {token}`. It never
  changes the sign-in email. Public `/verify-email?token=...` requires an explicit
  confirmation click (no scanner-triggered token consumption), and clears the
  token from the URL on success. Forgot-email recovery supports resend and changing
  the recovery address before verification.
- Billing copy discloses trial, automatic renewal and cancellation, and
  explicitly marks launch billing as sandbox validation—not live availability.

Focused offline validation:

```powershell
npm test -- tests/frontend/customer-access.test.tsx tests/frontend/subscription-section.test.tsx tests/frontend/account-recovery.test.tsx tests/frontend/parlay-optimizer.test.tsx
npx playwright test --config playwright.customer-launch.config.ts --workers=1
```

The customer-launch Playwright suite mocks all API calls and blocks non-local
network destinations; it covers 320, 390, 600, 900 and 1440px without a backend,
payment provider, outbound email or customer-account writes.

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
