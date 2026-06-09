"""Analytics / reporting endpoints (analysts, authorities, admins)."""
from flask import Blueprint, jsonify

from services import report_service
from services.ai_model_service import model_info
from middleware.rbac_middleware import require_permission

bp = Blueprint("reports", __name__)


@bp.get("/analytics")
@require_permission("analytics:read")
def analytics():
    return jsonify(report_service.build_analytics_report())


@bp.get("/overview")
@require_permission("analytics:read")
def overview():
    return jsonify(totals=report_service.system_overview())


@bp.get("/model-info")
@require_permission("analytics:read")
def ai_model_info():
    return jsonify(models=model_info())
