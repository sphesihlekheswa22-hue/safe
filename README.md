# 🛡️ SafeRoute AI

An intelligent **community risk prediction & service-continuity platform**.

SafeRoute AI tracks community events and risk signals, generates area-based risk
scores with a transparent scoring engine, recommends safe routes, and broadcasts
role-targeted alerts to citizens and institutions — all behind a strict,
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
- **Full CRUD** for events, alerts, routes, institutions and users.
- **Safe-route generation** returning GeoJSON + an aggregate corridor risk score.
- **Role-based dashboards** — KPI cards, area risk levels, live alert feed,
  event feed and safe-route suggestions, all loaded from the API (no mock data).
- **Analytics** with charts, an **audit log**, and a **realtime (SSE)** alert feed.
- **Tests**, **Dockerfile**, **docker-compose**, and reference **SQL schema**.

---

## 👥 Roles

| Role | Capabilities (summary) |
|------|------------------------|
| `PUBLIC_USER` | View dashboard, events, alerts (broadcast/own role), generate routes |
| `INSTITUTION_ADMIN` | + create events/alerts, view institutions |
| `TRANSPORT_OPERATOR` | + create events, manage routes |
| `GOVERNMENT_AUTHORITY` | + create alerts, recompute risk, view analytics |
| `SYSTEM_ANALYST` | + full analytics, recompute risk, see all alerts |
| `SYSTEM_ADMIN` | Everything + **exclusive** user & role management |

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
This creates all tables and inserts demo institutions, users, events, alerts and
routes (idempotent — safe to re-run).

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
| Institution Admin | `institution@saferoute.ai` | `Passw0rd!` |
| Transport Operator | `transport@saferoute.ai` | `Passw0rd!` |
| Government Authority | `gov@saferoute.ai` | `Passw0rd!` |
| System Analyst | `analyst@saferoute.ai` | `Passw0rd!` |

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

4. Render runs `python scripts/setup_db.py` on each deploy (creates tables + seeds demo data), then starts **gunicorn** on `$PORT`.

**Start command** (if not using `render.yaml`):

```bash
python scripts/setup_db.py && gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 wsgi:app
```

**Build command:** `pip install -r requirements.txt`

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
flask --app run set-role --email user@x.com --role SYSTEM_ANALYST
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
