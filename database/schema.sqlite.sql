-- SafeRoute AI — SQLite schema (singular table names).
-- Apply manually:
--   sqlite3 backend/saferoute_dev.db < database/schema.sqlite.sql
-- Or use the Python script (recommended):
--   python scripts/create_database.py

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS user (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            VARCHAR(120) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(40)  NOT NULL DEFAULT 'PUBLIC_USER',
    is_active       BOOLEAN      NOT NULL DEFAULT 1,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_user_email ON user(email);

CREATE TABLE IF NOT EXISTS event (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    location    VARCHAR(255) NOT NULL,
    latitude    REAL,
    longitude   REAL,
    severity    INTEGER      NOT NULL DEFAULT 1,
    source      VARCHAR(120) DEFAULT 'manual',
    created_by  INTEGER REFERENCES user(id),
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_event_location ON event(location);
CREATE INDEX IF NOT EXISTS ix_event_created_at ON event(created_at);

CREATE TABLE IF NOT EXISTS route (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    start_location  VARCHAR(255) NOT NULL,
    end_location    VARCHAR(255) NOT NULL,
    start_lat       REAL,
    start_lng       REAL,
    end_lat         REAL,
    end_lng         REAL,
    risk_score      REAL NOT NULL DEFAULT 0,
    geojson         JSON,
    created_by      INTEGER REFERENCES user(id),
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS risk_area (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    area_name        VARCHAR(255) NOT NULL UNIQUE,
    risk_score       REAL NOT NULL DEFAULT 0,
    sentiment_score  REAL NOT NULL DEFAULT 0,
    latitude         REAL,
    longitude        REAL,
    radius_km        REAL DEFAULT 2.5,
    updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_risk_area_area_name ON risk_area(area_name);

CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id     INTEGER REFERENCES user(id),
    actor_email  VARCHAR(255),
    action       VARCHAR(120) NOT NULL,
    target       VARCHAR(255),
    detail       TEXT,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_audit_log_created_at ON audit_log(created_at);

CREATE TABLE IF NOT EXISTS subscription (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES user(id),
    area_name   VARCHAR(255),
    channel     VARCHAR(40) NOT NULL DEFAULT 'in_app',
    active      BOOLEAN     NOT NULL DEFAULT 1,
    created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_setting (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         VARCHAR(80) NOT NULL UNIQUE,
    value       TEXT        NOT NULL,
    updated_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_system_setting_key ON system_setting(key);
