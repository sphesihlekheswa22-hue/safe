"""SafeRoute AI - application factory.

Creates the Flask app, wires extensions, registers API blueprints and the
template (page) routes, configures JWT JSON error handlers, and exposes CLI
commands for initializing and seeding the database.
"""
import os

from flask import Flask, render_template, jsonify, request
from config import Config
from extensions import db, migrate, jwt, bcrypt, cors
from logger import configure_logging, get_logger

# Resolve the frontend folders (sibling of the backend package).
_BACKEND_DIR = os.path.abspath(os.path.dirname(__file__))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
_TEMPLATE_DIR = os.path.join(_PROJECT_ROOT, "frontend", "templates")
_STATIC_DIR = os.path.join(_PROJECT_ROOT, "frontend", "static")


def create_app(config_class=Config):
    configure_logging()
    app = Flask(
        __name__,
        template_folder=_TEMPLATE_DIR,
        static_folder=_STATIC_DIR,
        static_url_path="/static",
    )
    app.config.from_object(config_class)

    # Initialize extensions.
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # Import models so SQLAlchemy/Migrate are aware of every table.
    import models  # noqa: F401

    # Register API blueprints (mounted under /api/...).
    from routes import register_api_blueprints

    register_api_blueprints(app)

    # Realtime (SSE) feed.
    from sockets.websocket import register as register_realtime

    register_realtime(app)

    # Request hooks (optional user loading into flask.g).
    from middleware import auth_middleware

    auth_middleware.register(app)

    _register_jwt_handlers(jwt)
    _register_pages(app)
    _register_cli(app)
    _register_error_handlers(app)

    # Skip heavy DB sync at gunicorn boot in production; preDeploy handles schema/seed.
    if os.environ.get("FLASK_ENV") != "production":
        with app.app_context():
            try:
                from sqlalchemy import inspect

                from models.event import Event
                from models.risk import RiskArea
                from services.geo_service import ensure_geo_columns, sync_area_coords, sync_event_coords

                tables = set(inspect(db.engine).get_table_names())
                if "risk_areas" in tables or "events" in tables:
                    ensure_geo_columns()
                dirty = False
                if "risk_areas" in tables:
                    for area in RiskArea.query.filter(RiskArea.latitude.is_(None)).all():
                        sync_area_coords(area)
                        dirty = True
                if "events" in tables:
                    for ev in Event.query.filter(Event.latitude.is_(None)).all():
                        sync_event_coords(ev)
                        dirty = True
                if dirty:
                    db.session.commit()
            except Exception:
                db.session.rollback()

    get_logger(__name__).info("SafeRoute AI application initialized.")
    return app


def _register_jwt_handlers(jwt_manager):
    """Return clean JSON for auth failures instead of HTML error pages."""

    @jwt_manager.unauthorized_loader
    def _missing_token(reason):
        return jsonify(error="Missing or invalid Authorization header.", detail=reason), 401

    @jwt_manager.invalid_token_loader
    def _invalid_token(reason):
        return jsonify(error="Invalid token.", detail=reason), 401

    @jwt_manager.expired_token_loader
    def _expired_token(header, payload):
        return jsonify(error="Token has expired. Please log in again."), 401

    @jwt_manager.revoked_token_loader
    def _revoked_token(header, payload):
        return jsonify(error="Token has been revoked."), 401


def _register_error_handlers(app):
    @app.errorhandler(404)
    def _not_found(err):
        # Keep API 404s as JSON; let page routes 404 render normally.
        if request.path.startswith("/api/"):
            return jsonify(error="Resource not found."), 404
        return render_template("login.html"), 404

    @app.errorhandler(500)
    def _server_error(err):
        return jsonify(error="Internal server error."), 500


def _register_pages(app):
    """Serve the Jinja template shells. Data is loaded client-side via the API."""

    @app.get("/")
    def index():
        return render_template("login.html")

    @app.get("/login")
    def login_page():
        return render_template("login.html")

    @app.get("/dashboard")
    def dashboard_page():
        return render_template("dashboard.html", heading="Dashboard")

    @app.get("/events")
    def events_page():
        return render_template("events.html", heading="Events & Risk Signals")

    @app.get("/routes")
    def routes_page():
        return render_template("routes.html", heading="Safe Routes")

    @app.get("/alerts")
    def alerts_page():
        return render_template("alerts.html", heading="Alerts")

    @app.get("/map")
    def map_page():
        return render_template("map.html", heading="Safety Map")

    @app.get("/profile")
    def profile_page():
        return render_template("profile.html", heading="My Profile")

    @app.get("/admin")
    def admin_page():
        return render_template("admin.html", heading="Admin Panel")

    @app.get("/analytics")
    def analytics_page():
        return render_template("analytics.html", heading="Analytics")

    @app.get("/institution")
    def institution_page():
        return render_template("institution.html", heading="Institution Safety")

    @app.get("/transport")
    def transport_page():
        return render_template("transport.html", heading="Transport Operations")

    @app.get("/government")
    def government_page():
        return render_template("government.html", heading="City Safety Command")

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")


def _register_cli(app):
    import click

    @app.cli.command("init-db")
    def init_db():
        """Create all database tables."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("seed")
    def seed():
        """Populate the database with demo data (admin, users, events...)."""
        from cli.seed import run_seed

        run_seed()
        click.echo("Seed data inserted.")

    @app.cli.command("refresh-events")
    def refresh_events():
        """Replace demo incidents with real South Africa events on the map."""
        from cli.seed import refresh_sa_events, refresh_sa_alerts

        count = refresh_sa_events()
        refresh_sa_alerts()
        click.echo(f"Loaded {count} real SA incidents. Alerts updated.")

    # Administrative CLI tools (create-admin, set-role, list-users).
    from cli import admin_tools

    admin_tools.register(app)


# Allow `flask --app app_factory run` and `python app_factory.py`.
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
