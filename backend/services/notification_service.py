"""Notification + audit service.

In the MVP, notifications are persisted as in-app Alerts and security-relevant
actions are written to the AuditLog. This is the seam where email / SMS / push
providers would be plugged in later.
"""
from extensions import db
from models.audit_log import AuditLog
from models.subscription import Subscription
from logger import get_logger

log = get_logger(__name__)


def record_audit(actor, action, target=None, detail=None):
    """Persist an audit log entry. ``actor`` may be a User or None."""
    entry = AuditLog(
        actor_id=getattr(actor, "id", None),
        actor_email=getattr(actor, "email", None),
        action=action,
        target=str(target) if target is not None else None,
        detail=detail,
    )
    db.session.add(entry)
    db.session.commit()
    log.info("AUDIT actor=%s action=%s target=%s", entry.actor_email, action, target)
    return entry


def recipients_for_alert(alert):
    """Return the user ids that should receive ``alert``.

    Combines role targeting with explicit area subscriptions.
    """
    from models.user import User

    if alert.target_role == "ALL":
        users = User.query.filter_by(is_active=True).all()
    else:
        users = User.query.filter_by(role=alert.target_role, is_active=True).all()

    ids = {u.id for u in users}
    # Anyone with an active subscription also receives broadcasts.
    subs = Subscription.query.filter_by(active=True).all()
    ids.update(s.user_id for s in subs)
    return sorted(ids)


def dispatch_alert(alert):
    """'Send' an alert. For now this just logs the intended recipients."""
    ids = recipients_for_alert(alert)
    log.info(
        "DISPATCH alert id=%s severity=%s -> %d recipient(s)",
        alert.id, alert.severity, len(ids),
    )
    return ids
