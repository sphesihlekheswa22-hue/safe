-- SafeRoute AI - reference PostgreSQL schema.
-- The application creates these tables automatically via SQLAlchemy
-- (`flask init-db` / scripts/setup_db.py). This file documents the schema and
-- can be applied manually if you prefer raw SQL.

CREATE TABLE IF NOT EXISTS institutions (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL UNIQUE,
    type        VARCHAR(80)  NOT NULL DEFAULT 'GENERIC',
    location    VARCHAR(255),
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(120) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(40)  NOT NULL DEFAULT 'PUBLIC_USER',
    institution_id  INTEGER REFERENCES institutions(id),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);

CREATE TABLE IF NOT EXISTS events (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    location    VARCHAR(255) NOT NULL,
    severity    INTEGER      NOT NULL DEFAULT 1,
    source      VARCHAR(120) DEFAULT 'manual',
    created_by  INTEGER REFERENCES users(id),
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_events_location ON events(location);
CREATE INDEX IF NOT EXISTS ix_events_created_at ON events(created_at);

CREATE TABLE IF NOT EXISTS routes (
    id              SERIAL PRIMARY KEY,
    start_location  VARCHAR(255) NOT NULL,
    end_location    VARCHAR(255) NOT NULL,
    risk_score      DOUBLE PRECISION NOT NULL DEFAULT 0,
    geojson         JSONB,
    created_by      INTEGER REFERENCES users(id),
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
    id           SERIAL PRIMARY KEY,
    message      TEXT         NOT NULL,
    severity     VARCHAR(20)  NOT NULL DEFAULT 'LOW',
    target_role  VARCHAR(40)  NOT NULL DEFAULT 'ALL',
    created_by   INTEGER REFERENCES users(id),
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_alerts_created_at ON alerts(created_at);

CREATE TABLE IF NOT EXISTS risk_areas (
    id               SERIAL PRIMARY KEY,
    area_name        VARCHAR(255) NOT NULL UNIQUE,
    risk_score       DOUBLE PRECISION NOT NULL DEFAULT 0,
    sentiment_score  DOUBLE PRECISION NOT NULL DEFAULT 0,
    updated_at       TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id           SERIAL PRIMARY KEY,
    actor_id     INTEGER REFERENCES users(id),
    actor_email  VARCHAR(255),
    action       VARCHAR(120) NOT NULL,
    target       VARCHAR(255),
    detail       TEXT,
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    area_name   VARCHAR(255),
    channel     VARCHAR(40) NOT NULL DEFAULT 'in_app',
    active      BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system_settings (
    id          SERIAL PRIMARY KEY,
    key         VARCHAR(80) NOT NULL UNIQUE,
    value       TEXT        NOT NULL,
    updated_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);
