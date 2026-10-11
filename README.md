# EV Shield

EV Shield is a responsive full-stack demo for security assessment and credential rotation across five fictional BMS profiles. Device connections, assessment evidence, and password changes are visibly labelled as simulated. It does not test or change physical BMS hardware.

## What is included

- React, TypeScript, Vite, Tailwind CSS, React Router, and Lucide icons.
- FastAPI REST API with OpenAPI docs at `/docs`.
- SQLAlchemy models and an Alembic initial schema migration.
- Persistent SQLite database; per-account simulator credentials use Argon2 hashes.
- Email or international phone signup/login with an HTTP-only JWT cookie.
- Five synthetic BMS profiles, backend-generated security assessments, history, retests, password rotation, and credential verification.
- Read-only Web Bluetooth device selection when supported. No device-specific services, commands, or hardware writes are configured.
- Frontend and backend automated tests.

## Run locally

Use Node.js 20+ and Python 3.10+. From the project root:

```sh
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
CI=true pnpm install
```

Set a unique random `SECRET_KEY` in `.env` before exposing the app beyond a local development machine. Defaults are configured for localhost and keep `REAL_BMS_WRITES=false`.

Start the backend in one terminal:

```sh
uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```sh
CI=true pnpm dev
```

Open [http://localhost:5173](http://localhost:5173). FastAPI Swagger UI is at [http://localhost:8000/docs](http://localhost:8000/docs).
Do not open `index.html` directly with a `file://` URL; Vite must serve the TypeScript modules for the app to render.

The backend creates the SQLite schema and seeds all five profiles on startup. To apply the Alembic migration explicitly before starting the API:

```sh
cd backend
python -m alembic -c alembic.ini upgrade head
cd ..
```

Seed the database manually at any time with:

```sh
cd backend
python -m app.seed
cd ..
```

## Judge demo

The local-only demo account is:

- Email: `judge@evshield.demo`
- Password: `Demo@1234`

Each seeded simulator device starts with its own account-scoped demo credential, `Demo@1234`. The credential help panel reveals it only in Simulator Mode and only before a device has been rotated. New passwords must be at least 10 characters and contain an uppercase letter, lowercase letter, number, and symbol.

1. Sign in with the demo account.
2. On **Bluetooth Connection**, connect `SecureBMS-S1`. Manufacturer, model, firmware, and interface are filled from the synthetic registry.
3. Open **BMS Security Assessment** and run the assessment. It should report PASS with 100/100 and full evidence coverage.
4. Open **Hardware Credential Management**, reveal the initial demo password, and select **Change Password**.
5. Enter `Demo@1234` as current and choose a new password such as `Shield@Pass2026` in both new password fields.
6. The success panel appears only after the API confirms that the new value is accepted and the previous value is rejected.
7. Use **Run Verification Again** to submit both values for a fresh backend check.
8. Connect `LegacyBMS-L1` to see a different result, or `UnknownBMS-U0` to see unknown evidence.

## Reset the demo

Use **Reset demo data** on Bluetooth Connection and confirm. This resets the signed-in account's synthetic credentials, rotations, assessment history, and active connection. It never contacts physical hardware. The five shared synthetic profiles are restored automatically.

## Tests

Backend tests:

```sh
cd backend
python -m pytest -q
cd ..
```

Frontend tests and production build:

```sh
CI=true pnpm test
CI=true pnpm build
```

## Authentication and recovery notes

Local demo authentication creates accounts immediately and sets a short-lived JWT in an HTTP-only cookie; no token is stored in browser local storage. No OTP, email, or SMS provider is configured, and EV Shield clearly says no message was sent. The recovery screen likewise reports that recovery delivery is unavailable until an identity provider is configured. The included judge credentials are for local demonstration only.

## Hardware safety

`REAL_BMS_WRITES=false` by default. The real Bluetooth view asks the browser to select a device only after a user click, does not connect to undocumented services or infer identity from the advertised name, and marks device identification as unverified. Credential rotation endpoints accept only the five seeded synthetic profiles with an active Simulator Mode session. UI and API state identify these operations as simulation-only.

## API overview

The documented REST routes cover authentication, profile listing and connection, identification, assessment and retest, credential status, rotation and verification, rotation history, capabilities, and scoped demo reset. OpenAPI request/response schemas are available at `/docs` and `/openapi.json`.

## Deployment

Build the frontend with `CI=true pnpm build` and serve the generated `dist/` directory from a static web host. Set `VITE_API_BASE` to the public HTTPS API origin before building. Run the backend with Uvicorn behind an HTTPS reverse proxy, and set `COOKIE_SECURE=true`, a unique random `SECRET_KEY`, and `CORS_ORIGINS` to the exact frontend origin. Keep `REAL_BMS_WRITES=false`. Point `DATABASE_URL` at a persistent SQLite volume (or configure another SQLAlchemy database URL); the database stores simulator state and must survive restarts. No production email/SMS OTP service or physical BMS adapter is included.

