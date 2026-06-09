"""API blueprint registration.

All API blueprints are mounted under ``/api``. Page (template) routes are
registered separately in ``app_factory.py``.
"""
from routes.auth import bp as auth_bp
from routes.dashboard import bp as dashboard_bp
from routes.events import bp as events_bp
from routes.routes import bp as routes_bp
from routes.alerts import bp as alerts_bp
from routes.admin import bp as admin_bp
from routes.ai import bp as ai_bp
from routes.institutions import bp as institutions_bp
from routes.reports import bp as reports_bp
from routes.health import bp as health_bp
from routes.chat import bp as chat_bp
from routes.institution_portal import bp as institution_portal_bp
from routes.transport_portal import bp as transport_portal_bp
from routes.government_portal import bp as government_portal_bp


def register_api_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(events_bp, url_prefix="/api/events")
    app.register_blueprint(routes_bp, url_prefix="/api/routes")
    app.register_blueprint(alerts_bp, url_prefix="/api/alerts")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(ai_bp, url_prefix="/api/ai")
    app.register_blueprint(institutions_bp, url_prefix="/api/institutions")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")
    app.register_blueprint(health_bp, url_prefix="/api/health")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    app.register_blueprint(institution_portal_bp, url_prefix="/api/institution")
    app.register_blueprint(transport_portal_bp, url_prefix="/api/transport")
    app.register_blueprint(government_portal_bp, url_prefix="/api/government")
