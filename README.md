# EV Shield

EV Shield is a software-first battery security management MVP for electric vehicles with BMS equipment. It includes a React/TypeScript dashboard, a FastAPI API, persistent SQLAlchemy storage, OTP development sign-in, an auditable simulator, assessment and remediation flows, incidents, and a passport JSON export.

**Safety boundary:** `REAL_BMS_WRITES=false` is the default. No physical-device adapters are implemented or validated. Credential rotation is therefore unavailable for hardware; the simulator never changes a physical BMS credential. The simulator is not a physical access-control gateway and does not close possible direct Bluetooth paths.

## Local setup

Requirements: Python 3.11+, Node.js 20+.

```sh
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

In a second terminal:

```sh
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. In development, sign in with `demo@evshield.local`; the page displays the generated one-time code. This is a local OTP challenge only: without a configured provider, no email or SMS is sent. API documentation is at <http://localhost:8000/docs>.

For local development, keep both the API and Vite development server running. Vite proxies `/api` requests to `127.0.0.1:8000`; if sign-in shows “Failed to fetch,” check that the API command above is still running and refresh the page.

## Docker

Set a long random `SECRET_KEY` in the environment, then run `docker compose up --build`. The compose file keeps real writes disabled, uses a persistent SQLite volume, and disables development OTP disclosure. Configure a real OTP delivery provider before exposing authentication beyond local development.

## Data and migrations

SQLite is used by default. Set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL for a production database. Models are in `backend/app/models`; migrations use Alembic:

```sh
cd backend
alembic -c alembic.ini upgrade head
```

Development demonstration data is seeded separately at API startup: `UP65-DEMO-042`, `UP65-DEMO-043`, and a clearly labelled incident. The assessment does not represent physical measurements.

## Tests and build

```sh
cd backend && pytest
cd frontend && npm test && npm run build
```

The simulator tests cover unauthorized shim rejection and non-forwarding, authorized simulated access, unknown-state preservation, and the unconditional `CONTROL_BATTERY` block. Real hardware integration, cross-tenant test coverage, production OTP delivery, upload storage, PDF generation, background scheduling, and a production secret manager are not implemented. The interface reports those constraints instead of asserting those validations occurred.

## Security and operational notes

- Backend endpoints require a signed session token; vehicle queries enforce owner filtering and return 404 for inaccessible vehicle IDs.
- The development challenge is generated per request, short-lived, and not logged. Production OTP delivery and rate limiting must be added before public deployment.
- Never submit BMS passwords or secret tokens in the compatibility form. No BMS secret is persisted.
- Session tokens use an eight-hour expiry. Change `SECRET_KEY` for every deployment and terminate TLS at the production ingress.
- Public aggregate reporting requires an authority role and suppresses totals below five.
- No GPS or trip tracking, arbitrary hardware commands, battery-control actions, firmware flashing, or live telemetry are provided.

## Bluetooth link

The **Bluetooth Connection** page uses the browser Web Bluetooth chooser to connect to a user-selected GATT device for transport only. The vehicle must be a non-demo registered record. The browser/device must support Web Bluetooth and the page must be served from HTTPS or localhost (desktop Chrome/Edge and some Android browsers). EV Shield does not enumerate undocumented services, read characteristics or telemetry, authenticate the BMS, or write configuration or credentials. Device name and Bluetooth identifier remain in browser memory; the backend audit records only link outcome. A successful GATT connection does not prove that the selected device is the registered BMS or that it is secure.
