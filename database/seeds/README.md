# Seeds

Demo data is generated programmatically (idempotent) rather than from static SQL
dumps, so it stays in sync with the models.

- Logic: `backend/cli/seed.py`
- Run via: `flask --app run seed` or `python scripts/setup_db.py`

It creates demo institutions, one user per role, sample events (which trigger
risk-area computation), alerts and saved routes.
