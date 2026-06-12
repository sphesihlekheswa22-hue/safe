"""Seed the database with demo users, events and routes.

Idempotent for users. Events are refreshed from the Gauteng catalog
via ``refresh_sa_events()`` (also available as ``flask refresh-events``).
"""
import os

from sqlalchemy import inspect, or_, text

from extensions import db
from models.user import User
from models.route import Route
from models.event import Event
from models.risk import RiskArea
from services import ingestion_service as ingestion, route_optimizer
from utils.rbac import Role
from utils.security import hash_password

from data.sa_events import REAL_SA_EVENTS


DEMO_PASSWORD = "Passw0rd!"

LEGACY_ROLES = (
    "INSTITUTION_ADMIN",
    "TRANSPORT_OPERATOR",
    "GOVERNMENT_AUTHORITY",
    "SYSTEM_ANALYST",
)

DEMO_PORTAL_EMAILS = (
    "institution@saferoute.ai",
    "transport@saferoute.ai",
    "gov@saferoute.ai",
    "analyst@saferoute.ai",
)

LEGACY_DEMO_LOCATIONS = [
    "Downtown", "North District", "South District", "East Side", "West Side",
    "Harbor", "Industrial Zone", "Central Station", "University", "Airport",
]

LEGACY_EVENT_SOURCES = ["seed-feed", "simulated", "demo"]

# Non-Gauteng locations from the previous KZN / national seed catalog.
LEGACY_NON_GAUTENG_LOCATIONS = [
    "Warwick Junction, Durban",
    "N3 Highway, Pinetown",
    "Umlazi",
    "Durban Harbour",
    "Florida Road, Durban",
    "UKZN",
    "Chatsworth",
    "Umhlanga",
    "Pinetown",
    "Johannesburg CBD",
    "Sandton",
    "Khayelitsha",
    "Cape Town CBD",
    "Phoenix",
    "Alexandra",
    "Durban CBD",
    "Durban Station",
]


def _get_or_create_user(name, email, password, role):
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
        )
        db.session.add(user)
    return user


def _purge_non_gauteng_routes() -> int:
    """Remove saved routes that reference legacy KZN / non-Gauteng locations."""
    removed = 0
    markers = (
        "durban", "umlazi", "ukzn", "pinetown", "cape town", "khayelitsha",
        "phoenix", "chatsworth", "umhlanga", "warwick", "kzn",
    )
    for route in Route.query.all():
        blob = f"{route.start_location or ''} {route.end_location or ''}".lower()
        if any(m in blob for m in markers):
            db.session.delete(route)
            removed += 1
    if removed:
        db.session.commit()
    return removed


def needs_gauteng_migration() -> bool:
    """True when legacy non-Gauteng incidents are still in the database."""
    patterns = [f"%{m}%" for m in ("durban", "umlazi", "ukzn", "cape town", "khayelitsha", "pinetown")]
    return (
        Event.query.filter(or_(*[Event.location.ilike(p) for p in patterns])).limit(1).count() > 0
        or Event.query.filter(Event.location.in_(LEGACY_NON_GAUTENG_LOCATIONS)).limit(1).count() > 0
    )


def needs_role_migration() -> bool:
    """True when legacy roles or institution schema remain in the database."""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "institutions" in tables:
        return True
    if User.query.filter(User.role.in_(LEGACY_ROLES)).limit(1).count() > 0:
        return True
    if "users" in tables:
        cols = {c["name"] for c in inspector.get_columns("users")}
        if "institution_id" in cols:
            return True
    return any(User.query.filter_by(email=email).limit(1).count() > 0 for email in DEMO_PORTAL_EMAILS)


def migrate_role_simplification() -> dict:
    """Remove legacy roles, demo portal users, and institution schema."""
    users_deleted = 0
    roles_updated = 0

    for email in DEMO_PORTAL_EMAILS:
        user = User.query.filter_by(email=email).first()
        if user:
            db.session.delete(user)
            users_deleted += 1

    for user in User.query.filter(User.role.in_(LEGACY_ROLES)).all():
        user.role = Role.PUBLIC_USER
        roles_updated += 1

    db.session.commit()

    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    institutions_dropped = False
    institution_column_dropped = False

    with db.engine.begin() as conn:
        if "institutions" in tables:
            try:
                conn.execute(text("DROP TABLE IF EXISTS institutions"))
                institutions_dropped = True
            except Exception:
                pass

        if "users" in tables:
            cols = {c["name"] for c in inspector.get_columns("users")}
            if "institution_id" in cols:
                try:
                    conn.execute(text("ALTER TABLE users DROP COLUMN institution_id"))
                    institution_column_dropped = True
                except Exception:
                    pass

    return {
        "users_deleted": users_deleted,
        "roles_updated": roles_updated,
        "institutions_dropped": institutions_dropped,
        "institution_column_dropped": institution_column_dropped,
    }


def refresh_sa_events() -> int:
    """Replace all events with the Gauteng (Pretoria) incident catalog."""
    Event.query.delete(synchronize_session=False)
    RiskArea.query.delete(synchronize_session=False)
    _purge_non_gauteng_routes()
    db.session.commit()

    created = ingestion.simulate_feed(REAL_SA_EVENTS, source="official-feed")
    return len(created)


def migrate_gauteng_data(*, reseed_routes: bool = True) -> dict:
    """Purge non-Gauteng demo data and reload Pretoria-focused catalog."""
    events_removed = Event.query.delete(synchronize_session=False)
    areas_removed = RiskArea.query.delete(synchronize_session=False)
    routes_removed = 0
    if reseed_routes:
        routes_removed = Route.query.delete(synchronize_session=False)
    db.session.commit()

    event_count = refresh_sa_events()

    routes_created = 0
    if reseed_routes and os.environ.get("SEED_SKIP_ROUTES", "").lower() not in ("1", "true"):
        try:
            for start, end in [("Pretoria Station", "Hatfield"), ("Soshanguve", "Pretoria CBD")]:
                result = route_optimizer.generate_route(start, end)
                db.session.add(Route(
                    start_location=result["start_location"],
                    end_location=result["end_location"],
                    start_lat=result.get("start_lat"),
                    start_lng=result.get("start_lng"),
                    end_lat=result.get("end_lat"),
                    end_lng=result.get("end_lng"),
                    risk_score=result["risk_score"],
                    geojson=result["geojson"],
                ))
                routes_created += 1
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            print(f"  Skipped demo routes (non-fatal): {exc}")

    return {
        "events_removed": events_removed,
        "risk_areas_removed": areas_removed,
        "routes_removed": routes_removed,
        "events_loaded": event_count,
        "routes_created": routes_created,
    }


def run_seed(refresh_events=True):
    db.create_all()

    if needs_role_migration():
        stats = migrate_role_simplification()
        print(f"  Role simplification migration: {stats}")

    admin_email = os.environ.get("SEED_ADMIN_EMAIL", "admin@saferoute.ai")
    admin_pw = os.environ.get("SEED_ADMIN_PASSWORD", "Admin#12345")
    admin_name = os.environ.get("SEED_ADMIN_NAME", "System Administrator")
    _get_or_create_user(admin_name, admin_email, admin_pw, Role.SYSTEM_ADMIN)
    _get_or_create_user("Paula Public", "public@saferoute.ai", DEMO_PASSWORD, Role.PUBLIC_USER)
    db.session.commit()

    if refresh_events:
        count = refresh_sa_events()
        print(f"  Loaded {count} Gauteng incidents with map coordinates.")

    if Route.query.count() == 0 and os.environ.get("SEED_SKIP_ROUTES", "").lower() not in ("1", "true"):
        try:
            for start, end in [("Pretoria Station", "Hatfield"), ("Soshanguve", "Pretoria CBD")]:
                result = route_optimizer.generate_route(start, end)
                db.session.add(Route(
                    start_location=result["start_location"],
                    end_location=result["end_location"],
                    start_lat=result.get("start_lat"),
                    start_lng=result.get("start_lng"),
                    end_lat=result.get("end_lat"),
                    end_lng=result.get("end_lng"),
                    risk_score=result["risk_score"],
                    geojson=result["geojson"],
                ))
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            print(f"  Skipped demo routes (non-fatal): {exc}")

    print("Seed complete.")
    print(f"  Admin login:   {admin_email} / {admin_pw}")
    print(f"  Demo user:     public@saferoute.ai / {DEMO_PASSWORD}")


if __name__ == "__main__":
    import sys

    _here = os.path.dirname(os.path.abspath(__file__))
    _backend = os.path.dirname(_here)
    _root = os.path.dirname(_backend)
    sys.path.insert(0, _backend)
    from dotenv import load_dotenv

    load_dotenv(os.path.join(_root, ".env"))
    from app_factory import create_app

    app = create_app()
    with app.app_context():
        if len(sys.argv) > 1 and sys.argv[1] == "migrate-gauteng":
            stats = migrate_gauteng_data()
            print("Gauteng migration complete:", stats)
        elif len(sys.argv) > 1 and sys.argv[1] == "migrate-roles":
            stats = migrate_role_simplification()
            print("Role simplification complete:", stats)
        else:
            run_seed()
