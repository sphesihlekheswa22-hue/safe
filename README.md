# 🛡️ SafeRoute AI

An intelligent **community risk prediction & service-continuity platform**.

SafeRoute AI tracks community events and risk signals, generates area-based risk
scores with a transparent scoring engine, recommends safe routes, and broadcasts
role-targeted notifications to citizens — all behind a strict,
server-enforced Role-Based Access Control (RBAC) system.

> Stack: **Flask · SQLAlchemy · PostgreSQL · Flask-JWT-Extended** on the backend,
> **Tailwind CSS + vanilla JS** (consuming the JSON API) on the frontend.

---

## ✨ Features

- **JWT authentication** with bcrypt password hashing (no plaintext, ever).
- **Strict RBAC** — roles are stored server-side and validated on every protected
  endpoint. Users can **never** choose or change their own role; only a
  `SYSTEM_ADMIN` can assign roles.
- **Risk engine** — `risk = severity·0.5 + density·0.3 + sentiment·0.2`
  (each component normalized to 0–100), recomputed whenever events change.
- **Full CRUD** for events, routes, and users.
- **Safe-route generation** returning GeoJSON + an aggregate corridor risk score.
- **Dashboard** — KPI cards, area risk levels, event feed and safe-route suggestions, all loaded from the API.
- **Admin panel** with user management, AI model controls, audit log, and emergency broadcast.
- **Tests**, **Dockerfile**, **docker-compose**, and reference **SQL schema**.

---

## 👥 Roles

| Role | Capabilities (summary) |
|------|------------------------|
| `PUBLIC_USER` | View dashboard, events, maps, generate routes, report incidents |
| `SYSTEM_ADMIN` | Everything public can do + user management, route delete, AI recompute, reports, emergency broadcast |

The full capability matrix lives in [`docs/rbac_matrix.md`](docs/rbac_matrix.md).

---

## 📁 Project structure

```
saferoute-ai/
├── run.py / wsgi.py            # entry points (dev / production)
├── requirements.txt
├── Dockerfile / docker-compose.yml
├── backend/
│   ├── app_factory.py          # Flask app factory
│   ├── config.py · extensions.py · logger.py
│   ├── models/                 # SQLAlchemy models
│   ├── routes/                 # API blueprints (auth, events, routes, …)
│   ├── services/               # risk engine, sentiment, routing, notifications
│   ├── ai/                     # model wrappers (+ hashing-embeddings stub)
│   ├── middleware/             # RBAC, auth hook, rate limiting
│   ├── schemas/ · repositories/ · utils/
│   └── cli/                    # seed + admin CLI tools
├── frontend/
│   ├── templates/ · components/  # Jinja shells + reusable partials
│   └── static/                   # css + js (api/app/dashboard/charts/…)
├── database/schema.sql
├── tests/ · scripts/ · docs/
```

See [`docs/architecture.md`](docs/architecture.md) for the request lifecycle and
[`docs/api_spec.md`](docs/api_spec.md) for the full endpoint reference.

---

## 🚀 Run locally

### Prerequisites
- Python 3.11+ (tested on 3.12)
- PostgreSQL 14+ (optional — see SQLite fallback below)

### 1. Install
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env       # then edit values
```
Set `DATABASE_URL` to your PostgreSQL instance, e.g.:
```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/saferoute
```
Create the database once (PostgreSQL):
```bash
createdb saferoute     # or: psql -U postgres -c "CREATE DATABASE saferoute;"
```

> **No PostgreSQL handy?** Leave `DATABASE_URL` unset and the app automatically
> falls back to a local SQLite file (`backend/saferoute_dev.db`). Everything
> works identically.

### 3. Create tables + seed demo data
```bash
python scripts/setup_db.py
```
This creates all tables and inserts demo users, events and routes (idempotent — safe to re-run).

### 4. Run
```bash
python run.py
```
Open **http://localhost:5000** and sign in.

### Demo accounts
| Role | Email | Password |
|------|-------|----------|
| System Admin | `admin@saferoute.ai` | `Admin#12345` |
| Public User | `public@saferoute.ai` | `Passw0rd!` |

---

## 🐳 Run with Docker

```bash
docker compose up --build
```
This starts PostgreSQL + the web app (gunicorn), auto-creates tables and seeds
demo data. App available at **http://localhost:5000**.

---

## 🚀 Deploy on Render (Neon PostgreSQL)

1. Push this repo to GitHub (or connect the existing remote).
2. In [Render](https://render.com), create a **New Web Service** and connect the repo.
   - Or use the included `render.yaml` blueprint (**New Blueprint**).
3. Set environment variables in the Render dashboard:

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | Your Neon connection string (paste as-is; `postgresql://` is fine) |
| `SECRET_KEY` | Long random string (or let Render generate) |
| `JWT_SECRET_KEY` | Long random string (or let Render generate) |
| `SEED_ADMIN_PASSWORD` | Production admin password |

4. Render runs `python scripts/setup_db.py` as a **pre-deploy** step (creates tables + seeds demo data), then starts **gunicorn** on `$PORT`.

**If you created the service manually in the Render dashboard**, set these exactly:

| Setting | Value |
|---------|--------|
| **Build command** | `pip install -r requirements.txt` |
| **Pre-deploy command** | `python scripts/setup_db.py` |
| **Start command** | `gunicorn --worker-class gthread --workers 1 --threads 4 --bind 0.0.0.0:$PORT --timeout 120 --graceful-timeout 30 wsgi:app` |
| **Health check path** | `/healthz` |

Do **not** use `--workers 2` on the free plan — it causes memory pressure and worker kills.

**Bad Gateway?** Usually the start command is wrong or `DATABASE_URL` is missing. Confirm `DATABASE_URL` (Neon) is set in Environment, then redeploy.

### Safety Assistant (Serper + live DB)

Set `SERPER_API_KEY` from [serper.dev](https://serper.dev) in `.env` or Render **Environment**. The chat combines:

- **SafeRoute database** — risk areas, incidents, alerts, routes (role-scoped)
- **Serper real-time search** — South Africa web & news (`gl=za`, SAST timestamps)

Optional: add `OPENAI_API_KEY` for an extra LLM layer (OpenAI / OpenRouter).

**Never commit API keys to git.**

---

## 🧪 Tests

```bash
pytest -q
```
Tests run against a throwaway SQLite database (no external services needed) and
cover authentication, RBAC enforcement, event CRUD + the risk engine, and the
general API surface.

---

## 🛠️ Useful CLI commands

```bash
# (uses run.py as the Flask app)
flask --app run init-db                 # create tables
flask --app run seed                    # seed demo data
flask --app run create-admin --email me@x.com --password "S3cretPass1" --name "Me"
flask --app run set-role --email user@x.com --role SYSTEM_ADMIN
flask --app run list-users
```

---

## 🔐 Security notes

- Passwords are bcrypt-hashed; the API never returns or stores plaintext.
- Role is a server-side column; registration always yields `PUBLIC_USER` and any
  client-supplied `role` field is ignored.
- Every protected endpoint uses the `require_permission` / `require_roles`
  decorator which loads the user from the DB and checks the **persisted** role,
  returning `401` (no/invalid token) or `403` (insufficient role).
- Secrets come from environment variables only — nothing is hard-coded.
- Login is protected by a simple in-memory rate limiter; input is validated on
  every write endpoint.
