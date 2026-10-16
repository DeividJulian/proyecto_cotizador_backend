# AI Quotation Engine: backend

A **FastAPI** API for freelancers who don't know how much to charge: the user describes their software project and
the app turns it into a complete quote. It detects the modules, estimates the hours with **PERT**, calculates the
price with the user's hourly rates and writes the commercial proposal.
Database: **PostgreSQL on Neon**. Login: **Google**.

## What does the "AI" do?
All natural language processing is implemented in plain Python, with no external APIs, and every result is explainable:

| Step | Technique |
|---|---|
| Scope analysis | Accent-free normalization, a catalog of 19 modules with keywords, and complexity signals per sentence |
| Estimation | Three-point PERT: (optimistic + 4·most likely + pessimistic) / 6, with ranges based on complexity |
| Work split | Each module is distributed among Backend, Frontend and UX/UI Design; QA, project management and deployment are calculated as a % of development |
| Financial calculation | direct cost → contingency → margin → discount → VAT, plus schedule and 40/30/30 payment milestones |
| Similar quotes | TF-IDF and cosine similarity implemented from scratch (only among the user's own quotes) |
| Proposal | Markdown document with 8 sections, amounts in Colombian pesos (COP) |

Scope descriptions are expected in Spanish: the module keywords in `services/catalogo.py` are Spanish.

## Getting started
```bash
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements-dev.txt
copy .env.example .env           # then paste your Neon connection string and Google client ID
uvicorn main:app --reload
```
Interactive documentation at http://127.0.0.1:8000/docs.

### Neon database
1. Create a project at https://neon.tech and copy the *connection string*.
2. Replace the `postgresql://` prefix with `postgresql+psycopg://` and keep only `?sslmode=require` at the end.
3. Paste it into `.env` as `DATABASE_URL`. Tables are created automatically on startup.

Neon puts the database to sleep after 5 minutes of inactivity: the first request may take a couple of seconds.
The engine uses `pool_pre_ping` and `pool_recycle` to reconnect without errors.

If the database still has tables from an older version of the schema, recreate them (this **deletes all data**):
`python reset_db.py --si`.

## Login with Google
1. The frontend shows the "Continue with Google" button and receives a Google **ID token**.
2. `POST /auth/google` with `{"credencial": "<ID token>"}`. The backend verifies the token's signature, audience
   (`GOOGLE_CLIENT_ID`), issuer and expiry, and that the email is verified.
3. The first login creates the account and loads the **market reference rates**. Next logins recover the same
   account (matched by the Google account id), with all its quotes.
4. The response includes the app's own JWT. Send it as `Authorization: Bearer <token>`. `GET /auth/me` returns the user.

There are no roles: every user sees and edits **only their own** quotes, items, proposals, rates and statistics.
Another user's data simply does not exist for them (404). In `/docs`, use **Authorize** to paste the token.

## Usage flow
1. Sign in with Google: your rates are already loaded (adjust them in `/tarifas` if you want, or restore them with
   `POST /tarifas/restablecer`). `POST /seed` loads example quotes.
2. `POST /cotizaciones` with the scope as free text (optionally, who the project is for: `cliente_nombre`, `cliente_empresa`).
3. `POST /cotizaciones/{id}/analizar`: modules, hours and price.
4. Optional adjustments: `PUT /cotizaciones/{id}` (margin, discount…) or `/items` (add, edit, remove). Everything is recalculated automatically.
5. `POST /cotizaciones/{id}/propuesta` and `GET .../propuesta/descargar`.
6. `POST /cotizaciones/{id}/estado` to track the proposal you sent to your client:
   `borrador` (draft) → `enviada` (sent) → `aceptada` (accepted) | `rechazada` (rejected).

A sent quote is frozen; to edit it, move it back to `borrador`.

## Main endpoints
| Group | Routes |
|---|---|
| Authentication | `POST /auth/google`, `GET /auth/me` |
| Scope | `POST /alcance/analizar`, `POST /alcance/estimar` (nothing is saved) |
| Finance | `POST /finanzas/simular` |
| Rates | CRUD at `/tarifas`, `POST /tarifas/restablecer`, `GET /tarifas/mercado` (public) |
| Quotes | CRUD, `/analizar`, `/resumen`, `/estado`, `/similares` |
| Items | `/cotizaciones/{id}/items` (GET, POST, PUT, DELETE) |
| Proposal | `/cotizaciones/{id}/propuesta` and `/descargar` |
| Analytics | `GET /estadisticas`, `POST /seed` |

## Tests
```bash
pytest
```
107 tests on SQLite. They never touch the Neon database and never call Google: a test verifier replaces the
Google token check, and the real verifier is tested with google-auth mocked.
