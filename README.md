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
62 tests on SQLite; they never touch the Neon database.
