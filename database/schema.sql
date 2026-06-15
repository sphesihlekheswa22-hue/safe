-- SafeRoute AI — PostgreSQL schema (singular table names).
-- Apply manually:
--   psql "$DATABASE_URL" -f database/schema.sql
-- Or use the Python script (recommended):
--   python scripts/create_database.py
--   python scripts/create_database.py --seed

BEGIN;

CREATE TABLE IF NOT EXISTS "user" (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(120) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(40)  NOT NULL DEFAULT 'PUBLIC_USER',
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_user_email ON "user"(email);

CREATE TABLE IF NOT EXISTS event (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    location    VARCHAR(255) NOT NULL,
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION,
    severity    INTEGER      NOT NULL DEFAULT 1,
    source      VARCHAR(120) DEFAULT 'manual',
    created_by  INTEGER REFERENCES "user"(id),
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_event_location ON event(location);
CREATE INDEX IF NOT EXISTS ix_event_created_at ON event(created_at);

CREATE TABLE IF NOT EXISTS route (
    id              SERIAL PRIMARY KEY,
    start_location  VARCHAR(255) NOT NULL,
    end_location    VARCHAR(255) NOT NULL,
    start_lat       DOUBLE PRECISION,
    start_lng       DOUBLE PRECISION,
    end_lat         DOUBLE PRECISION,
    end_lng         DOUBLE PRECISION,
    risk_score      DOUBLE PRECISION NOT NULL DEFAULT 0,
    geojson         JSONB,
    created_by      INTEGER REFERENCES "user"(id),
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_area (
    id               SERIAL PRIMARY KEY,
    area_name        VARCHAR(255) NOT NULL UNIQUE,
    risk_score       DOUBLE PRECISION NOT NULL DEFAULT 0,
    sentiment_score  DOUBLE PRECISION NOT NULL DEFAULT 0,
    latitude         DOUBLE PRECISION,
    longitude        DOUBLE PRECISION,
    radius_km        DOUBLE PRECISION DEFAULT 2.5,
    updated_at       TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_risk_area_area_name ON risk_area(area_name);

CREATE TABLE IF NOT EXISTS audit_log (
    id           SERIAL PRIMARY KEY,
    actor_id     INTEGER REFERENCES "user"(id),
    actor_email  VARCHAR(255),
    action       VARCHAR(120) NOT NULL,
    target       VARCHAR(255),
    detail       TEXT,
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_audit_log_created_at ON audit_log(created_at);

CREATE TABLE IF NOT EXISTS subscription (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES "user"(id),
    area_name   VARCHAR(255),
    channel     VARCHAR(40) NOT NULL DEFAULT 'in_app',
    active      BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system_setting (
    id          SERIAL PRIMARY KEY,
    key         VARCHAR(80) NOT NULL UNIQUE,
    value       TEXT        NOT NULL,
    updated_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_system_setting_key ON system_setting(key);

COMMIT;

-- Legacy plural tables (run once if upgrading an old database):
-- ALTER TABLE users RENAME TO "user";
-- ALTER TABLE events RENAME TO event;
-- ALTER TABLE routes RENAME TO route;
-- ALTER TABLE subscriptions RENAME TO subscription;
-- ALTER TABLE audit_logs RENAME TO audit_log;
-- ALTER TABLE risk_areas RENAME TO risk_area;
-- ALTER TABLE system_settings RENAME TO system_setting;
