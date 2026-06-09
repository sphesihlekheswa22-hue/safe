# Architecture

SafeRoute AI is a modular Flask application following a clean layered design.

## Layers

```
HTTP request
   │
   ▼
routes/  (blueprints)        ── thin controllers: parse, authorize, respond
   │
   ├── middleware/rbac_middleware  ── require_permission / require_roles
   ├── schemas/                    ── input validation (dependency-free)
   ▼
services/                    ── business logic (risk engine, routing, sentiment,
   │                             ingestion, notifications, reporting)
   ├── ai/                    ── model wrappers (sentiment, risk, embeddings stub)
   ▼
repositories/                ── data-access helpers over SQLAlchemy
   │
   ▼
models/  (SQLAlchemy ORM)     ── tables + serialization
   │
   ▼
PostgreSQL (or SQLite fallback)
```

## Request lifecycle (protected endpoint)

1. `app_factory.create_app()` wires extensions (SQLAlchemy, JWT, bcrypt, CORS,
   Migrate), registers blueprints, JWT JSON error handlers, page routes and CLI.
2. A request hits a blueprint view decorated with `@require_permission(...)`.
3. The decorator calls `verify_jwt_in_request()` (→ `401` if missing/invalid),
   loads the **persisted** `User` from the JWT identity, and checks the role
   against the permission matrix (→ `403` if not allowed).
4. The view validates input via a `schemas/*` function, delegates to a
   `services/*` function, which uses `repositories/*` to touch the database.
5. JSON is returned. Privileged mutations are written to the `audit_logs` table
   via `notification_service.record_audit`.

## Risk engine

`services/risk_engine.py` implements:

```
risk = severity_component·0.5 + density_component·0.3 + sentiment_component·0.2
```

Each component is normalized to 0–100:
- **severity** = average event severity (1–5) scaled to 0–100
- **density** = event count saturating at 10 → 0–100
- **sentiment** = lexicon sentiment in [-1,1] mapped so "very negative" → 100

Risk areas are recomputed and persisted whenever events change.

## Frontend

Server-rendered Jinja **shells** (with reusable `components/` partials) are
served by Flask. All data is fetched client-side from the JSON API using a small
`api.js` fetch wrapper that attaches the JWT. `app.js` guards pages, loads the
current user, and tailors the sidebar to the user's role. A Server-Sent-Events
endpoint (`/api/realtime/stream`) provides a live alert feed.

## Frontend ↔ backend contract

- Token is stored in `localStorage` and sent as `Authorization: Bearer <jwt>`.
- `401` responses cause the client to clear the session and redirect to `/login`.
- The sidebar shows admin/analytics links only for permitted roles, but this is
  **cosmetic** — the server independently authorizes every API call.
