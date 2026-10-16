# AI Quotation Engine: backend

A **FastAPI** API that turns the description of a software project into a complete quote:
it detects the modules, estimates the hours with **PERT**, calculates the price and writes the commercial proposal.
Database: **PostgreSQL on Neon**.

## What does the "AI" do?
All natural language processing is implemented in plain Python, with no external APIs, and every result is explainable:

| Step | Technique |
|---|---|
| Scope analysis | Accent-free normalization, a catalog of 19 modules with keywords, and complexity signals per sentence |
| Estimation | Three-point PERT: (optimistic + 4·most likely + pessimistic) / 6, with ranges based on complexity |
| Work split | Each module is distributed among Backend, Frontend and UX/UI Design; QA, project management and deployment are calculated as a % of development |
| Financial calculation | direct cost → contingency → margin → discount → VAT, plus schedule and 40/30/30 payment milestones |
| Similar quotes | TF-IDF and cosine similarity implemented from scratch |
| Proposal | Markdown document with 8 sections, amounts in Colombian pesos (COP) |

Scope descriptions are expected in Spanish: the module keywords in `services/catalogo.py` are Spanish.

## Getting started
```bash
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements-dev.txt
copy .env.example .env           # then paste your Neon connection string
uvicorn main:app --reload
```
Interactive documentation at http://127.0.0.1:8000/docs. For demo data: `POST /seed`.

### Neon database
1. Create a project at https://neon.tech and copy the *connection string*.
2. Replace the `postgresql://` prefix with `postgresql+psycopg://` and keep only `?sslmode=require` at the end.
3. Paste it into `.env` as `DATABASE_URL`. Tables are created automatically on startup.

Neon puts the database to sleep after 5 minutes of inactivity: the first request may take a couple of seconds.
The engine uses `pool_pre_ping` and `pool_recycle` to reconnect without errors.

## Login and roles
Passwordless login: the user enters their email and receives a **6-digit one-time code**.

1. `POST /auth/registro` (name, email, company) → emails a verification code.
2. `POST /auth/login` (email) → emails a login code (for accounts that already exist).
3. `POST /auth/verificar` (email, code) → returns a JWT. Send it as `Authorization: Bearer <token>`.
4. `GET /auth/me` → current user.

Codes expire after 10 minutes, can be used once, allow 5 attempts, and you must wait 30 seconds before requesting
another one. Only a hash of the code is stored.

| Role | Can do |
|---|---|
| `admin` | Everything: clients, rates, quotes, proposals, statistics, demo data and `/usuarios` (change roles). |
| `cliente` | See their own **sent** quotes (`GET /cotizaciones`, `/resumen`, `/propuesta`) and accept or reject them (`POST /cotizaciones/{id}/respuesta`). |

Emails listed in `ADMIN_EMAILS` become admins when they sign up; everyone else is a client linked to their client
record (matched by email, or created on verification). In `/docs`, use the **Authorize** button to paste the token.

### Sending emails
`EMAIL_BACKEND` chooses the provider: `consola` (prints the code in the terminal, default for local development),
`smtp` (e.g. Gmail with an app password, local only) or `brevo` (HTTP API, works on Render, whose free plan blocks
SMTP ports). See `.env.example`.

## Usage flow
1. `POST /tarifas`: hourly cost of each role (or `POST /seed`).
2. `POST /clientes` and `POST /cotizaciones` with the scope as free text.
3. `POST /cotizaciones/{id}/analizar`: modules, hours and price.
4. Optional adjustments: `PUT /cotizaciones/{id}` (margin, discount…) or `/items` (add, edit, remove). Everything is recalculated automatically.
5. `POST /cotizaciones/{id}/propuesta` and `GET .../propuesta/descargar`.
6. `POST /cotizaciones/{id}/estado`: `borrador` (draft) → `enviada` (sent) → `aceptada` (accepted) | `rechazada` (rejected).

A sent quote is frozen; to edit it, move it back to `borrador`.

## Main endpoints
| Group | Routes |
|---|---|
| Scope | `POST /alcance/analizar`, `POST /alcance/estimar` (nothing is saved) |
| Finance | `POST /finanzas/simular` |
| Clients and rates | CRUD at `/clientes` and `/tarifas` |
| Quotes | CRUD, `/analizar`, `/resumen`, `/estado`, `/similares` |
| Items | `/cotizaciones/{id}/items` (GET, POST, PUT, DELETE) |
| Proposal | `/cotizaciones/{id}/propuesta` and `/descargar` |
| Analytics | `GET /estadisticas`, `POST /seed` |

## Tests
```bash
pytest
```
140 tests on SQLite; they never touch the Neon database and never send real emails (they read the codes from
an in-memory outbox).
