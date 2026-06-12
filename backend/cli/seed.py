"""Seed the database with demo institutions, users, events and routes.

Idempotent for users/institutions. Events are refreshed from the real SA catalog
via ``refresh_sa_events()`` (also available as ``flask refresh-events``).
"""
import os

from extensions import db
from models.user import User
from models.institution import Institution
from models.route import Route
from models.event import Event
from services import ingestion_service as ingestion, route_optimizer
from utils.rbac import Role
from utils.security import hash_password

from data.sa_events import REAL_SA_EVENTS


DEMO_PASSWORD = "Passw0rd!"

# Legacy demo locations from the original NYC-themed seed.
LEGACY_DEMO_LOCATIONS = [
    "Downtown", "North District", "South District", "East Side", "West Side",
    "Harbor", "Industrial Zone", "Central Station", "University", "Airport",
]

LEGACY_EVENT_SOURCES = ["seed-feed", "simulated", "demo"]


def _get_or_create_institution(name, type_, location, **extra):
    inst = Institution.query.filter_by(name=name).first()
    if inst is None:
        inst = Institution(name=name, type=type_, location=location)
        db.session.add(inst)
        db.session.flush()
    for key, val in extra.items():
        if val is not None and hasattr(inst, key):
            setattr(inst, key, val)
    return inst


def _get_or_create_user(name, email, password, role, institution_id=None):
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            institution_id=institution_id,
        )
        db.session.add(user)
    return user


def refresh_sa_events() -> int:
    """Remove demo/legacy events and load the real South Africa incident catalog."""
    Event.query.filter(Event.source.in_(LEGACY_EVENT_SOURCES + ["official-feed"])).delete(
        synchronize_session=False
    )
    Event.query.filter(Event.location.in_(LEGACY_DEMO_LOCATIONS)).delete(
        synchronize_session=False
    )
    db.session.commit()

    created = ingestion.simulate_feed(REAL_SA_EVENTS, source="official-feed")
    return len(created)


def _migrate_legacy_institutions():
    """Upgrade old NYC-themed institution rows to South Africa demo data."""
    legacy_map = {
        "Central General Hospital": {
            "name": "UKZN Health Sciences",
            "type": "EDUCATION",
            "location": "UKZN",
            "latitude": -29.8089,
            "longitude": 30.9441,
            "radius_km": 10.0,
            "staff_count": 420,
            "student_count": 4800,
        },
        "Metro City Transit": {
            "name": "eThekwini Metro Transit",
            "type": "TRANSPORT",
            "location": "Durban CBD",
            "latitude": -29.8587,
            "longitude": 31.0218,
            "radius_km": 25.0,
            "staff_count": 85,
        },
        "City Emergency Management": {
            "name": "KZN Emergency Management",
            "type": "GOVERNMENT",
            "location": "Durban CBD",
            "latitude": -29.8587,
            "longitude": 31.0218,
            "radius_km": 12.0,
        },
    }
    for old_name, fields in legacy_map.items():
        inst = Institution.query.filter_by(name=old_name).first()
        if inst:
            for key, val in fields.items():
                setattr(inst, key, val)
    db.session.commit()


def run_seed(refresh_events=True):
    db.create_all()
    _migrate_legacy_institutions()

    # --- Institutions (South Africa) --------------------------------------
    durban_transit = _get_or_create_institution(
        "eThekwini Metro Transit", "TRANSPORT", "Durban CBD",
        latitude=-29.8587, longitude=31.0218, radius_km=25.0,
        staff_count=85, student_count=0,
    )
    ukzn_health = _get_or_create_institution(
        "UKZN Health Sciences", "EDUCATION", "UKZN",
        latitude=-29.8089, longitude=30.9441, radius_km=10.0,
        staff_count=420, student_count=4800,
    )
    kzn_gov = _get_or_create_institution(
        "KZN Emergency Management", "GOVERNMENT", "Durban CBD",
        latitude=-29.8587, longitude=31.0218, radius_km=12.0,
    )
    db.session.commit()

    # --- Admin (from env, falls back to defaults) -------------------------
    admin_email = os.environ.get("SEED_ADMIN_EMAIL", "admin@saferoute.ai")
    admin_pw = os.environ.get("SEED_ADMIN_PASSWORD", "Admin#12345")
    admin_name = os.environ.get("SEED_ADMIN_NAME", "System Administrator")
    _get_or_create_user(admin_name, admin_email, admin_pw, Role.SYSTEM_ADMIN)

    # --- One demo user per role ------------------------------------------
    _get_or_create_user("Paula Public", "public@saferoute.ai", DEMO_PASSWORD, Role.PUBLIC_USER)
    _get_or_create_user(
        "Ian Institution", "institution@saferoute.ai", DEMO_PASSWORD,
        Role.INSTITUTION_ADMIN, ukzn_health.id,
    )
    _get_or_create_user(
        "Tom Transit", "transport@saferoute.ai", DEMO_PASSWORD,
        Role.TRANSPORT_OPERATOR, durban_transit.id,
    )
    _get_or_create_user(
        "Gloria Gov", "gov@saferoute.ai", DEMO_PASSWORD,
        Role.GOVERNMENT_AUTHORITY, kzn_gov.id,
    )
    _get_or_create_user(
        "Alan Analyst", "analyst@saferoute.ai", DEMO_PASSWORD, Role.SYSTEM_ANALYST
    )
    db.session.commit()

    # --- Real SA events (always refresh on seed) --------------------------
    if refresh_events:
        count = refresh_sa_events()
        print(f"  Loaded {count} real SA incidents with map coordinates.")

    # --- Sample saved routes (optional; external OSRM can be slow on deploy) ---
    if Route.query.count() == 0 and os.environ.get("SEED_SKIP_ROUTES", "").lower() not in ("1", "true"):
        try:
            for start, end in [("Durban Station", "UKZN"), ("Umlazi", "Durban CBD")]:
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
    print(f"  Demo users:    public@ / institution@ / transport@ / analyst@saferoute.ai")
    print(f"  Demo password: {DEMO_PASSWORD}")


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
        run_seed()
